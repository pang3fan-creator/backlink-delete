#!/usr/bin/env python3
"""
backlink_db.py - lightweight SQLite helper for backlink submissions.

Supported commands:
  python3 backlink_db.py stats
  python3 backlink_db.py add-submission <site_id> <project> <status> [options]
"""

import sqlite3
import sys
from datetime import datetime
from typing import Optional

from backlink_common import DB_PATH, LOG_FILE, VALID_STATUSES, migrate_database


DEFAULT_NAME = "Stefan M."
DEFAULT_EMAIL = "pang3fan@gmail.com"


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_status(status: str) -> bool:
    if status not in VALID_STATUSES:
        print(f'❌ 非法状态: "{status}"')
        print(f'   允许的状态: {", ".join(VALID_STATUSES)}')
        return False
    return True


def log_to_file(
    site_url: str,
    project: str,
    submit_url: str,
    name: str,
    email: str,
    comment: str,
    result: str,
    comment_id: Optional[str] = None,
    target_url: str = "",
) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = now()
    entry = f"""=== {timestamp} ===
站点：{site_url}
项目：{project}
姓名：{name}
邮箱：{email}
网址：{submit_url}
文章：{target_url}
评论：{comment}
结果：{result}"""
    if comment_id:
        entry += f"，评论ID: {comment_id}"
    entry += "\n\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def add_submission() -> None:
    if len(sys.argv) < 5:
        print("用法: python3 backlink_db.py add-submission <site_id> <project> <status> [选项]")
        print(f'状态可选: {", ".join(VALID_STATUSES)}')
        print()
        print('选项:')
        print('  --notes "备注"')
        print('  --comment "评论内容"')
        print('  --comment-id "ID"')
        print('  --url "文章URL"')
        print('  --submit-url "网址"')
        print('  --reason "原因"')
        print('  --name "姓名"')
        print('  --email "邮箱"')
        sys.exit(1)

    site_id = sys.argv[2]
    project = sys.argv[3]
    status = sys.argv[4]
    if not validate_status(status):
        sys.exit(1)

    notes = ""
    comment = ""
    comment_id = ""
    target_url = ""
    submit_url = ""
    result_reason = ""
    name = DEFAULT_NAME
    email = DEFAULT_EMAIL

    i = 5
    while i < len(sys.argv):
        key = sys.argv[i]
        value = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        if key == "--notes":
            notes = value
            i += 2
        elif key == "--comment":
            comment = value
            i += 2
        elif key == "--comment-id":
            comment_id = value
            i += 2
        elif key == "--url":
            target_url = value
            i += 2
        elif key == "--submit-url":
            submit_url = value
            i += 2
        elif key == "--reason":
            result_reason = value
            i += 2
        elif key == "--name":
            name = value
            i += 2
        elif key == "--email":
            email = value
            i += 2
        else:
            print(f"❌ 未知选项: {key}")
            sys.exit(1)

    if not result_reason and notes:
        result_reason = notes
    if comment and not target_url:
        print("❌ 博客评论提交必须提供 --url 参数")
        sys.exit(1)

    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    now_ts = now()

    try:
        cursor.execute(
            """
            INSERT INTO submissions (
                site_id, project_name, status, notes, updated_at,
                submit_url, target_url, comment_text, comment_id, result_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, project_name) DO UPDATE SET
                status=?,
                notes=?,
                updated_at=?,
                submit_url=?,
                target_url=?,
                comment_text=?,
                comment_id=?,
                result_reason=?
            """,
            (
                site_id,
                project,
                status,
                notes,
                now_ts,
                submit_url,
                target_url,
                comment,
                comment_id,
                result_reason,
                status,
                notes,
                now_ts,
                submit_url,
                target_url,
                comment,
                comment_id,
                result_reason,
            ),
        )
        conn.commit()
        cursor.execute("SELECT site_url FROM sites WHERE id = ?", (site_id,))
        site = cursor.fetchone()
        site_url = site[0] if site else ""
        print("✅ 数据库记录已保存")
        print(f"   站点: {site_url}")
        print(f"   项目: {project}")
        print(f"   状态: {status}")
        if notes:
            print(f"   备注: {notes}")
        if result_reason:
            print(f"   原因: {result_reason}")
        if comment:
            log_to_file(
                site_url=site_url,
                project=project,
                submit_url=submit_url,
                name=name,
                email=email,
                comment=comment,
                result="成功" if status == "已提交" else status,
                comment_id=comment_id,
                target_url=target_url,
            )
            print(f"✅ 日志已记录到 {LOG_FILE}")
    except sqlite3.IntegrityError as e:
        print(f"❌ 数据库错误: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


def stats() -> None:
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sites")
    sites_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM submissions")
    subs_count = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT site_type, COUNT(*)
        FROM sites
        WHERE site_type IS NOT NULL AND site_type != ''
        GROUP BY site_type
        ORDER BY COUNT(*) DESC
        """
    )
    types = cursor.fetchall()
    cursor.execute(
        """
        SELECT project_name, COUNT(*)
        FROM submissions
        GROUP BY project_name
        ORDER BY project_name
        """
    )
    projects = cursor.fetchall()
    cursor.execute(
        """
        SELECT status, COUNT(*)
        FROM submissions
        GROUP BY status
        ORDER BY status
        """
    )
    statuses = cursor.fetchall()
    conn.close()

    print("📊 数据库统计")
    print(f"   站点总数: {sites_count}")
    print(f"   提交记录: {subs_count}")
    print()
    print("提交状态:")
    for status, count in statuses:
        print(f"   {status}: {count}")
    print()
    print("站点类型:")
    for stype, count in types:
        print(f"   {stype}: {count}")
    print()
    print("项目提交:")
    for project, count in projects:
        print(f"   {project}: {count}")


def main() -> None:
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 backlink_db.py stats")
        print("  python3 backlink_db.py add-submission <site_id> <project> <status> [选项]")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "stats":
        stats()
    elif cmd == "add-submission":
        add_submission()
    else:
        print(f"未知命令: {cmd}")
        print("可用命令: stats, add-submission")
        sys.exit(1)


if __name__ == "__main__":
    main()
