#!/usr/bin/env python3
"""Shared constants, SQLite migration helpers, and agent-browser integration for backlink tools."""

import os
import shutil
import subprocess
import sqlite3
import time
from pathlib import Path
from typing import Optional, Union


ROOT = Path(__file__).parent
DB_PATH = Path(os.environ.get("BACKLINKS_DB_PATH", ROOT / "backlinks.db"))
LOG_FILE = ROOT / "logs" / "submission.log"
AUTOMATION_BYPASS_ARG = "--disable-blink-features=AutomationControlled"

VALID_STATUSES = (
    "已提交",
    "待确认",
    "失败",
    "需付费",
    "需登录",
    "需验证码",
    "已失效",
    "跳过",
)

STATUS_SQL = ", ".join(f"'{status}'" for status in VALID_STATUSES)

HARD_WORTH_ZERO_PATTERNS = (
    "404",
    "not found",
    "dns",
    "name_not_resolved",
    "err_name_not_resolved",
    "could not resolve host",
    "nodename nor servname",
    "ssl",
    "certificate",
    "domain for sale",
    "域名出售",
    "site closed",
    "网站已关闭",
    "malware",
    "恶意",
    "no website/url field",
    "no website field",
    "no url field",
    "不接受外部链接",
)

LONG_TERM_TIMEOUT_PATTERNS = (
    "long-term timeout",
    "repeated timeout",
    "multiple timeouts",
    "长期超时",
    "多次超时",
)


def is_hard_worth_zero_reason(reason: str) -> bool:
    """Return True only for site-level blockers, not one-off automation failures."""
    if not reason:
        return False
    text = reason.lower()
    if any(pattern in text for pattern in HARD_WORTH_ZERO_PATTERNS):
        return True
    return any(pattern in text for pattern in LONG_TERM_TIMEOUT_PATTERNS)

# Agent-browser integration

_AGENT_BROWSER_PATH: Optional[str] = None


def agent_browser_available() -> bool:
    """Check if agent-browser CLI is installed and executable."""
    global _AGENT_BROWSER_PATH
    found = shutil.which("agent-browser")
    if found:
        _AGENT_BROWSER_PATH = found
        return True
    _AGENT_BROWSER_PATH = None
    return False


def get_agent_browser_proxy() -> Optional[str]:
    """Return proxy URL from env, or local default if available."""
    return os.environ.get("AGENT_BROWSER_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")


def run_agent_browser(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run an agent-browser command. Returns (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -2, "", "agent-browser not found"


def build_agent_browser_open_command(url: str, proxy: Optional[str] = None) -> list[str]:
    """Build a consistent agent-browser open command with anti-detection args."""
    command = ["agent-browser"]
    if proxy:
        command.extend(["--proxy", proxy])
    command.extend(["open", url, "--args", AUTOMATION_BYPASS_ARG])
    return command


def open_agent_browser(url: str, timeout: int = 30, proxy: Optional[str] = None) -> tuple[int, str, str]:
    """Open a page via agent-browser with the shared anti-detection arguments."""
    return run_agent_browser(build_agent_browser_open_command(url, proxy=proxy), timeout=timeout)


def close_agent_browser(all_sessions: bool = False) -> None:
    """Close agent-browser session(s). Never raises."""
    cmd = ["agent-browser", "close"]
    if all_sessions:
        cmd.append("--all")
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception:
        pass


def reset_agent_browser_daemon() -> None:
    """Fully reset agent-browser and Chrome processes so open --args take effect."""
    close_agent_browser(True)
    for pattern in ("agent-browser", "Chrome for Testing"):
        try:
            subprocess.run(["pkill", "-f", pattern], capture_output=True, timeout=10)
        except Exception:
            pass
    time.sleep(2)


def ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def table_sql(conn: sqlite3.Connection, table: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row[0] if row else ""


def project_view_name(project_name: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "_" for ch in project_name)
    safe = "_".join(part for part in safe.split("_") if part)
    return f"view_{safe or 'project'}"


def ensure_project_views(conn: sqlite3.Connection) -> None:
    projects = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT project_name FROM submissions WHERE project_name IS NOT NULL AND project_name != ''"
        )
    ]
    for project in projects:
        view_name = project_view_name(project)
        escaped_project = project.replace("'", "''")
        conn.execute(f'DROP VIEW IF EXISTS "{view_name}"')
        conn.execute(
            f"""
            CREATE VIEW "{view_name}" AS
            SELECT
                s.id AS site_id,
                s.site_url,
                s.site_type,
                s.weight,
                s.worth_submitting,
                s.skip_reason,
                s.consecutive_failures,
                sb.status,
                sb.notes,
                sb.submit_url,
                sb.target_url,
                sb.comment_text,
                sb.comment_id,
                sb.result_reason,
                sb.updated_at
            FROM sites s
            LEFT JOIN submissions sb
              ON s.id = sb.site_id
             AND sb.project_name = '{escaped_project}'
            """
        )


def submissions_status_check_is_current(conn: sqlite3.Connection) -> bool:
    sql = table_sql(conn, "submissions")
    return all(status in sql for status in VALID_STATUSES)


def rebuild_submissions_table(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("ALTER TABLE submissions RENAME TO submissions_old")
    conn.execute(
        f"""
        CREATE TABLE submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            status TEXT DEFAULT '已提交',
            notes TEXT,
            updated_at TEXT,
            submit_url TEXT,
            target_url TEXT,
            comment_text TEXT,
            comment_id TEXT,
            result_reason TEXT,
            UNIQUE(site_id, project_name),
            FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
            CHECK (status IN ({STATUS_SQL}))
        )
        """
    )
    conn.execute(
        """
        INSERT INTO submissions (
            id, site_id, project_name, status, notes, updated_at,
            submit_url, target_url, comment_text, comment_id, result_reason
        )
        SELECT
            id, site_id, project_name, status, notes, updated_at,
            submit_url, target_url, comment_text, comment_id, result_reason
        FROM submissions_old
        """
    )
    conn.execute("DROP TABLE submissions_old")
    conn.execute("PRAGMA foreign_keys = ON")


def migrate_database(db_path: Union[str, Path] = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        ensure_columns(
            conn,
            "sites",
            {
                "skip_reason": "TEXT",
                "consecutive_failures": "INTEGER DEFAULT 0",
            },
        )
        ensure_columns(
            conn,
            "submissions",
            {
                "submit_url": "TEXT",
                "target_url": "TEXT",
                "comment_text": "TEXT",
                "comment_id": "TEXT",
                "result_reason": "TEXT",
            },
        )
        if not submissions_status_check_is_current(conn):
            rebuild_submissions_table(conn)
        ensure_project_views(conn)
        conn.commit()
    finally:
        conn.close()


def validate_status(status: str) -> bool:
    return status in VALID_STATUSES
