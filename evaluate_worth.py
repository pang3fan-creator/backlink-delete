#!/usr/bin/env python3
"""
评估所有 worth=NULL 站点的 worth_submitting 字段。

工作方式：
  1. 打开页面 → 检测访问性
  2. 硬障碍 (404/DNS/SSL/无URL字段) → worth=0
  3. 软障碍 (登录/验证码/Cloudflare/超时) → 保留 NULL，记录到报告
  4. 访问成功 → 按 site_type 执行 DOM 检测
  5. blog_comment 确认有表单+URL字段 → worth=1 (--apply)
  6. 其他类型找到表单+URL字段 → 报告但不自动标记 worth=1
"""

import argparse
import json
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path

from backlink_common import (
    DB_PATH,
    close_agent_browser,
    is_hard_worth_zero_reason,
    migrate_database,
    open_agent_browser,
    reset_agent_browser_daemon,
    run_agent_browser,
)

PROGRESS_FILE = Path("evaluate_progress.json")
REPORT_FILE = Path("evaluate_worth_report.md")


def aggressive_reset_daemon():
    """More thorough daemon reset that handles this environment's Chrome path."""
    close_agent_browser(True)
    for pattern in ("agent-browser", "remote-debugging-port"):
        try:
            subprocess.run(["pkill", "-9", "-f", pattern], capture_output=True, timeout=10)
        except Exception:
            pass
    time.sleep(2)

# site_type groups that share evaluation logic
SUBMISSION_TYPES = {"form", "directory", "pending", "listing", "search_engine"}
BLOG_COMMENT_TYPES = {"blog_comment"}
ARTICLE_TYPES = {"article"}
PROFILE_TYPES = {"profile"}

# Broad patterns for URL fields in submission forms
URL_FIELD_PATTERNS = [
    'input[type="url"]',
    'input[name*="url" i]',
    'input[id*="url" i]',
    'input[placeholder*="url" i]',
    'input[name*="website" i]',
    'input[id*="website" i]',
    'input[name*="link" i]',
    'input[id*="link" i]',
    'input[name*="site" i]',
    'input[id*="site" i]',
    'input[name*="homepage" i]',
    'input[id*="homepage" i]',
    'input[placeholder*="website" i]',
    'input[placeholder*="link" i]',
]
URL_SELECTOR = ", ".join(URL_FIELD_PATTERNS)


def agent_browser(cmd, timeout=15):
    return run_agent_browser(["agent-browser"] + cmd, timeout=timeout)


def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {"processed": [], "total": 0, "started_at": None}


def save_progress(progress):
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2))


def mark_site_worth_zero(site_id, reason):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE sites SET worth_submitting = 0, skip_reason = ? WHERE id = ?",
        (reason, site_id),
    )
    conn.commit()
    conn.close()


def mark_site_worth_one(site_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE sites SET worth_submitting = 1, skip_reason = NULL WHERE id = ?",
        (site_id,),
    )
    conn.commit()
    conn.close()


def check_accessibility(url):
    """Open page and check if it's accessible. Returns (accessible, reason)."""
    rc, _, err = open_agent_browser(url, timeout=25)
    if rc != 0:
        err_lower = err.lower()
        if "cloudflare" in err_lower or "challenge" in err_lower:
            return False, "Cloudflare verification wall"
        elif "timeout" in err_lower or "timed_out" in err_lower:
            return False, "Page timeout"
        elif "connection_closed" in err_lower or "connection_refused" in err_lower:
            return False, "Connection refused/closed"
        elif "ssl" in err_lower:
            return False, "SSL error"
        elif "blocked" in err_lower:
            return False, "Blocked by client"
        elif "404" in err_lower or "not found" in err_lower:
            return False, "404 not found"
        elif "dns" in err_lower or "name_not_resolved" in err_lower or "could not resolve" in err_lower:
            return False, "DNS resolution failed"
        elif "certificate" in err_lower:
            return False, "SSL certificate error"
        else:
            return False, err.strip()[:80]

    rc, body, _ = agent_browser(["get", "text", "body"], timeout=5)
    body_lower = body.lower()
    if "cloudflare" in body_lower and ("verify" in body_lower or "challenge" in body_lower):
        return False, "Cloudflare challenge on page"
    if "captcha" in body_lower or "recaptcha" in body_lower or "hcaptcha" in body_lower:
        return False, "Captcha required"
    if "wp-login" in body_lower or "please log in" in body_lower:
        return False, "Login wall"

    # Check for JS redirect to about:blank (common anti-bot pattern)
    rc_url, out_url, _ = agent_browser(["eval", "window.location.href"], timeout=3)
    if rc_url == 0 and "about:blank" in out_url:
        return False, "Page redirected to about:blank (anti-bot protection)"

    return True, "OK"


def check_blog_comment_form():
    """Check for standard blog comment form with Website field."""
    js = """
    (() => {
        const form = document.querySelector('#commentform, .comment-form, #respond form, form[action*="comment"]');
        if (!form) return JSON.stringify({has_form: false, has_url_field: false, form_type: 'none', detail: ''});

        const comment = form.querySelector('textarea[name="comment"], textarea[id*="comment"]');
        if (!comment) return JSON.stringify({has_form: false, has_url_field: false, form_type: 'no_comment_field', detail: ''});

        const url = form.querySelector('input[name="url"], input[name="website"], input[id*="url"]');
        const hasUrl = !!url;
        const isHidden = form.offsetParent === null;
        const closedText = document.body.innerText.toLowerCase();
        const isClosed = closedText.includes('comments are closed') || closedText.includes('commenting is closed');

        return JSON.stringify({
            has_form: !isClosed && !isHidden,
            has_url_field: hasUrl,
            form_type: isClosed ? 'closed' : (isHidden ? 'hidden' : 'visible'),
            detail: ''
        });
    })()
    """
    rc, stdout, stderr = agent_browser(["eval", js], timeout=8)
    if rc != 0:
        return None, f"eval failed: {stderr.strip()[:80]}"

    raw = stdout.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    try:
        check = json.loads(raw)
    except json.JSONDecodeError:
        return None, f"JSON parse failed: {raw[:80]}"

    if not isinstance(check, dict):
        return None, f"eval returned non-object: {str(check)[:80]}"

    has_form = check.get("has_form", False)
    has_url = check.get("has_url_field", False)
    ft = check.get("form_type", "")

    if not has_form:
        if ft == "none":
            return False, "No comment form in DOM"
        elif ft == "no_comment_field":
            return False, "Comment form exists but no comment textarea"
        elif ft == "closed":
            return False, "Comments are closed"
        elif ft == "hidden":
            return False, "Comment form is hidden (display:none)"
        else:
            return False, f"Form type={ft}"
    if not has_url:
        return False, "No Website/URL field in comment form"
    return True, "OK"


def check_submission_form():
    """Check for any submission form that has a URL field."""
    js = """
    (() => {
        const forms = document.querySelectorAll('form');
        const results = [];
        for (const form of forms) {
            const isHidden = form.offsetParent === null;
            if (isHidden) continue;

            const inputs = form.querySelectorAll('input, textarea, select');
            if (inputs.length < 2) continue;

            const urlFields = form.querySelectorAll('""" + URL_SELECTOR + """');
            const hasUrlField = urlFields.length > 0;

            const labels = form.querySelectorAll('label');
            const labelTexts = Array.from(labels).map(l => l.textContent.trim().toLowerCase());
            const hasUrlLabel = labelTexts.some(t => /website|url|site/i.test(t));

            results.push({
                id: form.id || '',
                action: (form.action || '').slice(0, 60),
                inputCount: inputs.length,
                hasUrlField: hasUrlField,
                hasUrlLabel: hasUrlLabel,
                urlFieldNames: Array.from(urlFields).map(f => f.name || f.id || '?')
            });
        }
        return JSON.stringify(results);
    })()
    """
    rc, stdout, stderr = agent_browser(["eval", js], timeout=8)
    if rc != 0:
        return None, f"eval failed: {stderr.strip()[:80]}"

    raw = stdout.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    try:
        forms = json.loads(raw)
    except json.JSONDecodeError:
        return None, f"JSON parse failed: {raw[:80]}"

    if not isinstance(forms, list):
        return None, f"unexpected response: {str(forms)[:80]}"

    valid_forms = [f for f in forms if f.get("hasUrlField")]
    if valid_forms:
        detail = f"form #{len(valid_forms)} with URL field"
        return True, detail
    if len(forms) > 0:
        return False, f"{len(forms)} form(s) found, none with URL field"
    return False, "No forms found on page"


def check_article_form():
    """Check if article submission page has a URL/link field."""
    js = """
    (() => {
        const bodyText = document.body.innerText.toLowerCase();

        const forms = document.querySelectorAll('form');
        for (const form of forms) {
            const urlFields = form.querySelectorAll('""" + URL_SELECTOR + """');
            if (urlFields.length > 0) {
                return JSON.stringify({
                    found: true,
                    detail: 'form with URL field',
                    urlFieldNames: Array.from(urlFields).map(f => f.name || f.id || '?')
                });
            }
            const textareas = form.querySelectorAll('textarea');
            if (textareas.length >= 1) {
                const inputs = form.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button])');
                if (inputs.length >= 1) {
                    return JSON.stringify({
                        found: true,
                        detail: 'form with textarea + input (possible submission form)',
                        urlFieldNames: Array.from(inputs).map(f => f.name || f.id || '?')
                    });
                }
            }
        }

        const urlInputs = document.querySelectorAll('""" + URL_SELECTOR + """');
        if (urlInputs.length > 0) {
            return JSON.stringify({
                found: true,
                detail: 'URL field found outside form',
                urlFieldNames: Array.from(urlInputs).map(f => f.name || f.id || '?')
            });
        }

        return JSON.stringify({found: false, detail: 'no submission form or URL field detected'});
    })()
    """
    rc, stdout, stderr = agent_browser(["eval", js], timeout=8)
    if rc != 0:
        return None, f"eval failed: {stderr.strip()[:80]}"

    raw = stdout.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return None, f"JSON parse failed: {raw[:80]}"

    if not isinstance(result, dict):
        return None, f"unexpected response: {str(result)[:80]}"

    if result.get("found"):
        return True, result["detail"]
    return False, result.get("detail", "no form found")


def check_profile_site():
    """Check if profile page has website/URL in visible content."""
    js = """
    (() => {
        const bodyText = document.body.innerText.toLowerCase();

        const urlPatterns = [/website/i, /homepage/i, /https?:\\/\\//];
        const hasWebsiteText = urlPatterns.some(p => p.test(bodyText));

        const inputs = document.querySelectorAll('""" + URL_SELECTOR + """');
        const hasUrlField = inputs.length > 0;

        const editable = document.querySelectorAll('form, input, textarea, [contenteditable]');
        const hasEditableForm = editable.length > 0;

        return JSON.stringify({
            hasWebsiteText: hasWebsiteText,
            hasUrlField: hasUrlField,
            hasEditableForm: hasEditableForm,
            isForumProfile: /profile|member|user/.test(window.location.pathname)
        });
    })()
    """
    rc, stdout, stderr = agent_browser(["eval", js], timeout=8)
    if rc != 0:
        return None, f"eval failed: {stderr.strip()[:80]}"

    raw = stdout.strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].replace('\\"', '"').replace('\\\\', '\\')
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return None, f"JSON parse failed: {raw[:80]}"

    if not isinstance(result, dict):
        return None, f"unexpected response: {str(result)[:80]}"

    if result.get("hasEditableForm") and result.get("hasUrlField"):
        return True, "Profile page has editable form with URL field"

    if result.get("isForumProfile"):
        return False, "Forum profile page - needs login to edit"

    return False, "No URL field or editable form found"


def get_null_sites(site_type=None):
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if site_type:
        cur.execute(
            "SELECT id, site_url, site_type FROM sites WHERE worth_submitting IS NULL AND site_type = ? ORDER BY id",
            (site_type,),
        )
    else:
        cur.execute(
            "SELECT id, site_url, site_type FROM sites WHERE worth_submitting IS NULL ORDER BY id"
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def evaluate_site(site_id, url, site_type):
    result = {
        "id": site_id,
        "url": url,
        "type": site_type,
        "accessible": False,
        "has_form": False,
        "has_url_field": False,
        "reason": "",
        "detail": "",
        "decision": "keep_null",
    }

    is_accessible, reason = check_accessibility(url)
    result["accessible"] = is_accessible
    result["reason"] = reason

    if not is_accessible:
        if is_hard_worth_zero_reason(reason):
            result["decision"] = "worth_zero"
        else:
            result["decision"] = "keep_null"
        return result

    if site_type in BLOG_COMMENT_TYPES:
        ok, detail = check_blog_comment_form()
    elif site_type in SUBMISSION_TYPES:
        ok, detail = check_submission_form()
    elif site_type in ARTICLE_TYPES:
        ok, detail = check_article_form()
    elif site_type in PROFILE_TYPES:
        ok, detail = check_profile_site()
    else:
        ok, detail = check_submission_form()

    if ok is None:
        result["reason"] = detail
        result["detail"] = detail
        result["decision"] = "keep_null"
    elif ok:
        result["has_form"] = True
        result["has_url_field"] = True
        result["reason"] = "OK"
        result["detail"] = detail
        if site_type in BLOG_COMMENT_TYPES:
            result["decision"] = "worth_one"
        else:
            result["decision"] = "report_only"
    else:
        result["reason"] = detail
        result["detail"] = detail
        if site_type in BLOG_COMMENT_TYPES and is_hard_worth_zero_reason(detail):
            result["decision"] = "worth_zero"
        else:
            result["decision"] = "keep_null"

    return result


def print_stats_header(sites, progress):
    total = len(sites)
    done = len(progress.get("processed", []))
    remaining = total - done
    print(f"📋 待评估: {total} 个 NULL 站点 | 已处理: {done} | 剩余: {remaining}")


def main():
    parser = argparse.ArgumentParser(description="评估所有 worth=NULL 站点的 worth_submitting 字段")
    parser.add_argument("--type", help="只处理指定类型 (如 blog_comment)")
    parser.add_argument("--limit", type=int, help="最多处理多少个站点")
    parser.add_argument("--apply", action="store_true", help="应用结果到数据库")
    parser.add_argument("--resume", action="store_true", help="从上次进度续跑")
    parser.add_argument("--report", default="evaluate_worth_report.md", help="报告输出路径")
    args = parser.parse_args()

    migrate_database(DB_PATH)

    # Backup before modifications
    if args.apply:
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"backlinks-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
        shutil.copy2(DB_PATH, backup_path)
        print(f"💾 数据库已备份: {backup_path}")

    sites = get_null_sites(args.type)
    if not sites:
        print("✅ 没有 worth=NULL 的站点")
        return

    if args.limit:
        sites = sites[: args.limit]

    progress = load_progress() if args.resume else {"processed": [], "total": len(sites), "started_at": None}
    if progress["started_at"] is None:
        progress["started_at"] = datetime.now().isoformat()
        progress["total"] = len(sites)

    processed_ids = set(progress.get("processed", []))
    pending = [s for s in sites if s[0] not in processed_ids]

    if not pending:
        print("✅ 所有站点已处理完毕（从进度文件）")
        return

    print(f"📋 待评估: {len(sites)} 个 NULL 站点 | 已处理: {len(processed_ids)} | 本次新处理: {len(pending)}")
    print()

    results = {
        "worth_zero": [],
        "worth_one": [],
        "report_only": [],
        "keep_null": [],
    }

    total = len(sites)
    for i, (sid, url, stype) in enumerate(pending, 1):
        global_seq = len(processed_ids) + i
        prefix = f"[{global_seq}/{total}]"
        url_short = url[:70]
        print(f"{prefix} ({stype}) {url_short}", end=" ... ", flush=True)

        aggressive_reset_daemon()
        r = evaluate_site(sid, url, stype)

        if r["decision"] == "worth_zero":
            print(f"❌ worth=0: {r['reason']}")
            if args.apply:
                mark_site_worth_zero(sid, r["reason"])
        elif r["decision"] == "worth_one":
            print(f"✅ worth=1")
            if args.apply:
                mark_site_worth_one(sid)
        elif r["decision"] == "report_only":
            print(f"⚠️ 有表单但仅报告 (不自动标记): {r['detail']}")
        else:
            print(f"🔍 保留 NULL: {r['reason']}")

        results[r["decision"]].append(r)

        processed_ids.add(sid)
        progress["processed"] = list(processed_ids)
        save_progress(progress)

        aggressive_reset_daemon()
        if i < len(pending):
            time.sleep(0.5)

    print()
    print("=" * 70)
    print("📊 评估结果汇总")
    print(f"   总处理: {len(pending)}")
    print(f"   ❌ 硬障碍 → worth=0: {len(results['worth_zero'])}")
    print(f"   ✅ 确认有表单 (blog_comment) → worth=1: {len(results['worth_one'])}")
    print(f"   ⚠️ 有表单 (其他类型, 仅报告): {len(results['report_only'])}")
    print(f"   🔍 保留 NULL (待复查): {len(results['keep_null'])}")
    print()

    # Generate report
    report_lines = []
    report_lines.append(f"# evaluate_worth 评估报告")
    report_lines.append(f"")
    report_lines.append(f"- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"- **总处理**: {len(pending)}")
    report_lines.append(f"- **模式**: {'--apply (已写入数据库)' if args.apply else '只报告，未写入数据库'}")
    report_lines.append(f"")
    report_lines.append(f"| 结果 | 数量 |")
    report_lines.append(f"|------|------|")
    report_lines.append(f"| ❌ worth=0 (硬障碍) | {len(results['worth_zero'])} |")
    report_lines.append(f"| ✅ worth=1 (blog_comment 确认有表单) | {len(results['worth_one'])} |")
    report_lines.append(f"| ⚠️ 有表单-仅报告 (非 blog_comment) | {len(results['report_only'])} |")
    report_lines.append(f"| 🔍 保留 NULL (待复查) | {len(results['keep_null'])} |")
    report_lines.append(f"")

    for section_title, key in [
        ("## ❌ 硬障碍 → worth=0", "worth_zero"),
        ("## ✅ 确认有表单 → worth=1", "worth_one"),
        ("## ⚠️ 有表单 (仅报告, 未标记)", "report_only"),
        ("## 🔍 保留 NULL (待复查)", "keep_null"),
    ]:
        items = results[key]
        if not items:
            continue
        report_lines.append(section_title)
        report_lines.append(f"")
        report_lines.append(f"| ID | 类型 | URL | 原因 |")
        report_lines.append(f"|----|------|-----|------|")
        for r in items:
            reason = r["reason"].replace("|", "/")
            url = r["url"].replace("|", "/")
            report_lines.append(f"| {r['id']} | {r['type']} | {url} | {reason} |")
        report_lines.append(f"")

    report = "\n".join(report_lines)

    report_path = Path(args.report)
    report_path.write_text(report)
    print(f"📄 完整报告: {report_path}")
    print()
    print(report)

    if not args.apply:
        print("💡 要应用结果到数据库，加 --apply 参数")
        print()


if __name__ == "__main__":
    main()
