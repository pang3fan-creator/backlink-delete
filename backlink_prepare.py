#!/usr/bin/env python3
"""
批量文章内容提取工具：提交前快速了解站点内容，辅助生成相关评论。

用法：
  python3 backlink_prepare.py --project "tryschedule.com"
  python3 backlink_prepare.py --project "tryschedule.com" --limit 5
  python3 backlink_prepare.py --project "tryschedule.com" --format json
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
DB_PATH = ROOT / "backlinks.db"


def agent_browser(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        r = subprocess.run(["agent-browser"] + cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -2, "", "agent-browser not found"


def _ab(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    return agent_browser(cmd, timeout=timeout)


def close_browser():
    try:
        subprocess.run(["agent-browser", "close"], capture_output=True, timeout=5)
    except Exception:
        pass


def extract_article_summary(url: str) -> dict:
    """
    Open a page with agent-browser and extract title + text preview.
    Returns {'title': str, 'preview': str, 'lang': str, 'success': bool, 'error': str}
    """
    result = {'title': '', 'preview': '', 'lang': '', 'success': False, 'error': ''}

    rc, _, err = _ab(["open", url, "--args", "--disable-blink-features=AutomationControlled"], timeout=30)
    if rc != 0:
        result['error'] = err.strip() or 'open failed'
        return result

    rc_title, title, _ = _ab(["get", "text", "title"], timeout=5)
    if rc_title == 0:
        result['title'] = title.strip()[:200]

    rc_lang, lang, _ = _ab(["eval", "document.documentElement.lang || 'unknown'"], timeout=5)
    if rc_lang == 0:
        raw = lang.strip()
        if raw.startswith('"') and raw.endswith('"'):
            raw = raw[1:-1]
        result['lang'] = raw[:20]

    rc_text, text, _ = _ab(["get", "text", "body"], timeout=8)
    if rc_text == 0:
        cleaned = re.sub(r'\s+', ' ', text).strip()
        result['preview'] = cleaned[:500]

    result['success'] = True
    return result


def get_pending_sites(project: str, limit: Optional[int] = None) -> list[tuple[int, str]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    query = '''
        SELECT s.id, s.site_url
        FROM sites s
        LEFT JOIN submissions sb ON s.id = sb.site_id AND sb.project_name = ?
        WHERE s.site_type = 'blog_comment'
          AND s.worth_submitting = 1
          AND sb.id IS NULL
        ORDER BY s.id
    '''
    cur.execute(query, (project,))
    rows = cur.fetchall()
    conn.close()
    if limit:
        rows = rows[:limit]
    return rows


def main():
    parser = argparse.ArgumentParser(description="批量提取文章内容，辅助生成评论")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--limit", type=int, default=5, help="最多处理站点数")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    args = parser.parse_args()

    pending = get_pending_sites(args.project, args.limit)

    if not pending:
        print("✅ 没有待处理的 worth=1 站点")
        return

    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"🔍 提取 {len(pending)} 个站点内容 — {args.project}")
    print()

    for i, (sid, url) in enumerate(pending, 1):
        print(f"[{i}/{len(pending)}] ID={sid}", end=" ... ", flush=True)
        summary = extract_article_summary(url)
        summary['id'] = sid
        summary['url'] = url
        results.append(summary)

        if summary['success']:
            print(f"✅ {summary['lang']}")
        else:
            print(f"❌ {summary['error']}")

        close_browser()
        if i < len(pending):
            time.sleep(0.5)

    print()
    print("=" * 70)

    if args.format == "json":
        output = []
        for r in results:
            output.append({
                'id': r['id'],
                'url': r['url'],
                'title': r['title'],
                'preview': r['preview'][:300],
                'lang': r['lang'],
                'success': r['success'],
                'error': r.get('error', ''),
            })
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for r in results:
            if r['success']:
                print(f"\n#{r['id']} | {r['lang'].upper()} | {r['title']}")
                print(f"   URL: {r['url']}")
                preview = r['preview'][:300]
                print(f"   预览: {preview}...")
                print(f"   → 评论建议方向：需围绕文章主题自然融入 schedule/planning 话题")
            else:
                print(f"\n#{r['id']} | ❌ 提取失败: {r['error']}")
                print(f"   URL: {r['url']}")

    print()
    print(f"📝 共处理 {len(results)} 个站点 — {timestamp}")


if __name__ == "__main__":
    main()
