#!/usr/bin/env python3
"""Shared constants, SQLite migration helpers, and agent-browser integration for backlink tools."""

import os
import shutil
import subprocess
import sqlite3
from pathlib import Path
from typing import Optional, Union


ROOT = Path(__file__).parent
DB_PATH = Path(os.environ.get("BACKLINKS_DB_PATH", ROOT / "backlinks.db"))
EXCEL_PATH = Path(os.environ.get("BACKLINKS_EXCEL_PATH", ROOT / "backlinks.xlsx"))
LOG_FILE = ROOT / "logs" / "submission.log"

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


def close_agent_browser(all_sessions: bool = False) -> None:
    """Close agent-browser session(s). Never raises."""
    cmd = ["agent-browser", "close"]
    if all_sessions:
        cmd.append("--all")
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception:
        pass


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
            target_url, comment_text, comment_id, result_reason
        )
        SELECT
            id, site_id, project_name, status, notes, updated_at,
            target_url, comment_text, comment_id, result_reason
        FROM submissions_old
        """
    )
    conn.execute("DROP TABLE submissions_old")
    conn.execute("PRAGMA foreign_keys = ON")


def migrate_database(db_path: Union[str, Path] = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        ensure_columns(conn, "sites", {"skip_reason": "TEXT"})
        ensure_columns(
            conn,
            "submissions",
            {
                "target_url": "TEXT",
                "comment_text": "TEXT",
                "comment_id": "TEXT",
                "result_reason": "TEXT",
            },
        )
        if not submissions_status_check_is_current(conn):
            rebuild_submissions_table(conn)
        conn.commit()
    finally:
        conn.close()


def validate_status(status: str) -> bool:
    return status in VALID_STATUSES
