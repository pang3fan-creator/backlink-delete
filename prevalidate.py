#!/usr/bin/env python3
"""
批量预检脚本：提交前验证 worth=1 站点是否真的有评论表单 + Website 字段

用法：
python3 prevalidate.py --project heicpdf.to
python3 prevalidate.py --project heicpdf.to --apply   (自动标记不合格站点)

检查逻辑（DOM 级别，不依赖页面文字）：
1. 页面是否可达
2. DOM 中是否有评论表单 (textarea[name=comment] 或 #commentform 或 #respond form)
3. 表单中是否有 Website 字段 (input[name=url] 或 input[name=website])
"""

import argparse
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
DB_PATH = ROOT / "backlinks.db"


def agent_browser(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """Run agent-browser command. Returns (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(["agent-browser"] + cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -2, "", "agent-browser not found"


def close_browser():
    try:
        subprocess.run(["agent-browser", "close"], capture_output=True, timeout=5)
    except Exception:
        pass


def check_site(site_url: str) -> dict:
    """
    预检单个站点。返回:
    {
        'accessible': bool,
        'has_form': bool,
        'has_url_field': bool,
        'reason': str (失败原因),
        'comment': str (额外备注)
    }
    """
    result = {'accessible': False, 'has_form': False, 'has_url_field': False, 'reason': '', 'comment': ''}

    # 1. 打开页面
    rc, _, err = agent_browser(["open", site_url], timeout=25)
    if rc != 0:
        err_lower = err.lower()
        if 'cloudflare' in err_lower or 'challenge' in err_lower:
            result['reason'] = 'Cloudflare verification wall'
        elif 'timeout' in err_lower or 'timed_out' in err_lower:
            result['reason'] = 'Page timeout'
        elif 'connection_closed' in err_lower or 'connection_refused' in err_lower:
            result['reason'] = 'Connection refused/closed'
        elif 'ssl' in err_lower:
            result['reason'] = 'SSL error'
        elif 'blocked' in err_lower:
            result['reason'] = 'Blocked by client'
        elif '404' in err_lower or 'not found' in err_lower:
            result['reason'] = '404 not found'
        else:
            result['reason'] = f'Navigation failed: {err.strip()[:80]}'
        return result

    result['accessible'] = True

    # 2. Check for Cloudflare / login wall in the page
    rc, body, _ = agent_browser(["get", "text", "body"], timeout=5)
    body_lower = body.lower()
    if 'cloudflare' in body_lower and ('verify' in body_lower or 'challenge' in body_lower):
        result['accessible'] = False
        result['reason'] = 'Cloudflare challenge on page'
        return result
    if 'wp-login' in body_lower or 'please log in' in body_lower:
        result['accessible'] = False
        result['reason'] = 'Login wall'
        return result

    # 3. DOM-level check for comment form
    js = """
    (() => {
        // Check for comment form existence
        const form = document.querySelector('#commentform, .comment-form, #respond form, form[action*="comment"]');
        if (!form) return JSON.stringify({has_form: false, has_url_field: false, form_type: 'none'});

        // Check for comment textarea
        const comment = form.querySelector('textarea[name="comment"], textarea[id*="comment"]');
        if (!comment) return JSON.stringify({has_form: false, has_url_field: false, form_type: 'no_comment_field'});

        // Check for URL/Website field
        const url = form.querySelector('input[name="url"], input[name="website"], input[id*="url"]');
        const hasUrl = !!url;

        // Check if form seems disabled (comment closed)
        const isHidden = form.offsetParent === null;
        const closedText = document.body.innerText.toLowerCase();
        const isClosed = closedText.includes('comments are closed') || closedText.includes('commenting is closed');

        return JSON.stringify({
            has_form: !isClosed && !isHidden,
            has_url_field: hasUrl,
            form_type: isClosed ? 'closed' : (isHidden ? 'hidden' : 'visible'),
            comment_field: comment ? (comment.name || comment.id) : null,
            url_field: url ? (url.name || url.id) : null
        });
    })()
    """

    rc, stdout, stderr = agent_browser(["eval", js], timeout=8)
    if rc != 0:
        err_msg = stderr.strip()[:80] if stderr else 'unknown'
        result['reason'] = f'eval failed: {err_msg}'
        return result

    # agent-browser eval wraps JSON in an extra layer of quotes
    raw = stdout.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    try:
        check = json.loads(raw)
    except json.JSONDecodeError:
        result['reason'] = f'JSON parse failed: {raw[:80]}'
        return result

    if not isinstance(check, dict):
        result['reason'] = f'eval returned non-object: {str(check)[:80]}'
        return result

    result['has_form'] = check.get('has_form', False)
    result['has_url_field'] = check.get('has_url_field', False)

    if not result['has_form']:
        ft = check.get('form_type', '')
        if ft == 'none':
            result['reason'] = 'No comment form in DOM'
        elif ft == 'no_comment_field':
            result['reason'] = 'Comment form exists but no comment textarea'
        elif ft == 'closed':
            result['reason'] = 'Comments are closed'
        elif ft == 'hidden':
            result['reason'] = 'Comment form is hidden (display:none)'
        else:
            result['reason'] = f'Form type={ft}'
    elif not result['has_url_field']:
        result['reason'] = 'No Website/URL field in comment form'
    else:
        result['reason'] = 'OK'

    result['comment'] = f"form={check.get('form_type', '?')}, comment={check.get('comment_field', '?')}, url={check.get('url_field', '?')}"

    return result


def get_pending_sites(project: str) -> list[tuple[int, str]]:
    """Get all worth=1 unsubmitted blog_comment sites for a project."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT s.id, s.site_url
        FROM sites s
        LEFT JOIN submissions sb ON s.id = sb.site_id AND sb.project_name = ?
        WHERE s.site_type = 'blog_comment'
          AND s.worth_submitting = 1
          AND sb.id IS NULL
        ORDER BY s.id
    ''', (project,))
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_site(site_id: int, worth: int, reason: str):
    """Mark a site worth=0 with skip_reason."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        'UPDATE sites SET worth_submitting = ?, skip_reason = ? WHERE id = ?',
        (worth, reason, site_id)
    )
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="批量预检 worth=1 站点是否有有效评论表单")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--apply", action="store_true", help="自动标记不合格站点为 worth=0")
    args = parser.parse_args()

    print(f"🔍 预检项目: {args.project}")
    print()

    pending = get_pending_sites(args.project)

    if not pending:
        print("✅ 没有待预检的 worth=1 站点")
        return

    print(f"📋 待检查: {len(pending)} 个站点\n")

    passed = []
    failed = []

    for i, (sid, url) in enumerate(pending, 1):
        prefix = f"[{i}/{len(pending)}]"
        print(f"{prefix} {url[:70]}", end=" ... ", flush=True)

        result = check_site(url)

        if result['accessible'] and result['has_form'] and result['has_url_field']:
            print(f"✅ ({result['comment']})")
            passed.append((sid, url))
        else:
            print(f"❌ {result['reason']}")
            failed.append((sid, url, result['reason']))

        try:
            close_browser()
        except Exception:
            pass
        if i < len(pending):
            time.sleep(0.5)

    print()
    print("=" * 60)
    print(f"📊 预检结果: {len(pending)} 个站点")
    print(f"   ✅ 通过 (可提交): {len(passed)}")
    print(f"   ❌ 不通过: {len(failed)}")
    print()

    if passed:
        print("✅ 可提交的站点:")
        for sid, url in passed:
            print(f"   ID={sid}: {url}")
        print()

    if failed:
        print("❌ 不通过的站点:")
        for sid, url, reason in failed:
            print(f"   ID={sid}: {url}")
            print(f"      原因: {reason}")
        print()

    if args.apply and failed:
        print("🔧 自动标记不通过站点为 worth=0 ...")
        for sid, url, reason in failed:
            mark_site(sid, 0, reason)
            print(f"   ID={sid}: worth=0 ({reason})")
        print()

    if not args.apply and failed:
        print("💡 要自动标记不通过站点，加 --apply 参数")
        print()


if __name__ == "__main__":
    main()
