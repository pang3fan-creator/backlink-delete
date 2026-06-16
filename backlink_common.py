#!/usr/bin/env python3
"""Shared constants and SQLite migration helpers for backlink tools."""

import os
import sqlite3
from pathlib import Path
from typing import Union


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
