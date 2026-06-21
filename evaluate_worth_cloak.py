#!/usr/bin/env python3
"""
评估所有 worth=NULL 站点的 worth_submitting 字段（使用 CloakBrowser）。
与 evaluate_worth.py 不同，本版本使用 CloakBrowser (stealth Playwright)，
反检测能力更强，能绕过 Cloudflare 等 bot 检测。
"""

import argparse
import json
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from backlink_common import (
    DB_PATH,
    is_hard_worth_zero_reason,
    migrate_database,
)

from cloakbrowser import launch
from playwright.sync_api import TimeoutError as PwTimeout, Error as PwError

PROGRESS_FILE = Path("evaluate_cloak_progress.json")

SUBMISSION_TYPES = {"form", "directory", "pending", "listing", "search_engine"}
BLOG_COMMENT_TYPES = {"blog_comment"}
ARTICLE_TYPES = {"article"}
PROFILE_TYPES = {"profile"}

URL_FIELD_SELECTOR = (
    'input[type="url"], '
    'input[name*="url" i], input[id*="url" i], input[placeholder*="url" i], '
    'input[name*="website" i], input[id*="website" i], '
    'input[name*="link" i], input[id*="link" i], '
    'input[name*="site" i], input[id*="site" i], '
    'input[name*="homepage" i], input[id*="homepage" i], '
    'input[placeholder*="website" i], input[placeholder*="link" i]'
)


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


def check_page(page, url):
    result = {
        "accessible": False,
        "reason": "",
    }

    try:
        response = page.goto(url, timeout=25000, wait_until="commit")
    except PwTimeout:
        result["reason"] = "Page timeout"
        return result
    except PwError as e:
        msg = str(e).lower()
        if "timeout" in msg or "timed out" in msg:
            result["reason"] = "Page timeout"
        elif "ssl" in msg or "certificate" in msg:
            result["reason"] = "SSL error"
        elif "dns" in msg or "name_not_resolved" in msg or "could not resolve" in msg:
            result["reason"] = "DNS resolution failed"
        elif "connection_refused" in msg or "connection_closed" in msg or "econnrefused" in msg:
            result["reason"] = "Connection refused/closed"
        elif "404" in msg or "not found" in msg:
            result["reason"] = "404 not found"
        elif "blocked" in msg:
            result["reason"] = "Blocked by client"
        elif "err_name_not_resolved" in msg:
            result["reason"] = "DNS resolution failed"
        else:
            result["reason"] = str(e)[:80]
        return result
    except Exception as e:
        result["reason"] = f"Navigation failed: {str(e)[:80]}"
        return result

    # Let JS render (SPA forms, lazy-loaded content)
    try:
        page.wait_for_timeout(3000)
    except Exception:
        pass

    if "about:blank" in page.url:
        result["reason"] = "Page redirected to about:blank (anti-bot protection)"
        return result

    try:
        body = page.inner_text("body").lower()
    except Exception:
        result["reason"] = "Page body empty or inaccessible"
        return result

    if "cloudflare" in body and ("verify" in body or "challenge" in body):
        result["reason"] = "Cloudflare challenge on page"
        return result
    if "captcha" in body or "recaptcha" in body or "hcaptcha" in body:
        result["reason"] = "Captcha required"
        return result
    if "wp-login" in body or "please log in" in body:
        result["reason"] = "Login wall"
        return result

    result["accessible"] = True
    return result


def check_blog_comment_form(page):
    js = """
    () => {
        const form = document.querySelector('#commentform, .comment-form, #respond form, form[action*="comment"]');
        if (!form) return {has_form: false, has_url_field: false, form_type: 'none'};

        const comment = form.querySelector('textarea[name="comment"], textarea[id*="comment"]');
        if (!comment) return {has_form: false, has_url_field: false, form_type: 'no_comment_field'};

        const url = form.querySelector('input[name="url"], input[name="website"], input[id*="url"]');
        const isHidden = form.offsetParent === null;
        const closedText = document.body.innerText.toLowerCase();
        const isClosed = closedText.includes('comments are closed') || closedText.includes('commenting is closed');

        return {
            has_form: !isClosed && !isHidden,
            has_url_field: !!url,
            form_type: isClosed ? 'closed' : (isHidden ? 'hidden' : 'visible'),
        };
    }
    """
    try:
        result = page.evaluate(js)
    except Exception as e:
        return None, f"eval failed: {str(e)[:80]}"

    if not isinstance(result, dict):
        return None, f"unexpected response: {str(result)[:80]}"

    has_form = result.get("has_form", False)
    has_url = result.get("has_url_field", False)
    ft = result.get("form_type", "")

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


def check_submission_form(page):
    js = """
    (sel) => {
        const forms = document.querySelectorAll('form');
        const results = [];
        for (const form of forms) {
            const isHidden = form.offsetParent === null;
            if (isHidden) continue;

            const inputs = form.querySelectorAll('input, textarea, select');
            if (inputs.length < 2) continue;

            let urlFields;
            try {
                urlFields = form.querySelectorAll(sel);
            } catch(e) {
                urlFields = [];
            }
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
        return results;
    }
    """
    try:
        forms = page.evaluate(js, URL_FIELD_SELECTOR)
    except Exception as e:
        return None, f"eval failed: {str(e)[:80]}"

    if not isinstance(forms, list):
        return None, f"unexpected response: {str(forms)[:80]}"

    valid = [f for f in forms if f.get("hasUrlField")]
    if valid:
        names = valid[0].get("urlFieldNames", [])
        return True, f"form with URL field: {', '.join(names)}"
    if len(forms) > 0:
        return False, f"{len(forms)} form(s) found, none with URL field"
    return False, "No forms found on page"


def check_article_form(page):
    js = """
    (sel) => {
        const forms = document.querySelectorAll('form');
        for (const form of forms) {
            let urlFields;
            try {
                urlFields = form.querySelectorAll(sel);
            } catch(e) { urlFields = []; }
            if (urlFields.length > 0) {
                return {found: true, detail: 'form with URL field', names: Array.from(urlFields).map(f => f.name || f.id || '?')};
            }
            const textareas = form.querySelectorAll('textarea');
            if (textareas.length >= 1) {
                const inputs = form.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button])');
                if (inputs.length >= 1) {
                    return {found: true, detail: 'form with textarea + input', names: Array.from(inputs).map(f => f.name || f.id || '?')};
                }
            }
        }
        let urlInputs;
        try { urlInputs = document.querySelectorAll(sel); } catch(e) { urlInputs = []; }
        if (urlInputs.length > 0) {
            return {found: true, detail: 'URL field found outside form', names: Array.from(urlInputs).map(f => f.name || f.id || '?')};
        }
        return {found: false, detail: 'no submission form or URL field detected'};
    }
    """
    try:
        result = page.evaluate(js, URL_FIELD_SELECTOR)
    except Exception as e:
        return None, f"eval failed: {str(e)[:80]}"

    if not isinstance(result, dict):
        return None, f"unexpected response: {str(result)[:80]}"

    if result.get("found"):
        return True, result["detail"]
    return False, result.get("detail", "no form found")


def check_profile_site(page):
    js = """
    (sel) => {
        const bodyText = document.body.innerText.toLowerCase();
        const hasWebsiteText = /website|homepage|https?:\\/\\//i.test(bodyText);

        let inputs;
        try { inputs = document.querySelectorAll(sel); } catch(e) { inputs = []; }
        const hasUrlField = inputs.length > 0;

        const editable = document.querySelectorAll('form, input, textarea, [contenteditable]');
        const hasEditableForm = editable.length > 0;

        return {
            hasWebsiteText: hasWebsiteText,
            hasUrlField: hasUrlField,
            hasEditableForm: hasEditableForm,
            isForumProfile: /profile|member|user/.test(window.location.pathname)
        };
    }
    """
    try:
        result = page.evaluate(js, URL_FIELD_SELECTOR)
    except Exception as e:
        return None, f"eval failed: {str(e)[:80]}"

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


def evaluate_site(page, sid, url, stype):
    result = {
        "id": sid,
        "url": url,
        "type": stype,
        "accessible": False,
        "has_form": False,
        "has_url_field": False,
        "reason": "",
        "detail": "",
        "decision": "keep_null",
    }

    page_result = check_page(page, url)
    result["accessible"] = page_result["accessible"]
    result["reason"] = page_result["reason"]

    if not result["accessible"]:
        if is_hard_worth_zero_reason(result["reason"]):
            result["decision"] = "worth_zero"
        return result

    if stype in BLOG_COMMENT_TYPES:
        ok, detail = check_blog_comment_form(page)
    elif stype in SUBMISSION_TYPES:
        ok, detail = check_submission_form(page)
    elif stype in ARTICLE_TYPES:
        ok, detail = check_article_form(page)
    elif stype in PROFILE_TYPES:
        ok, detail = check_profile_site(page)
    else:
        ok, detail = check_submission_form(page)

    if ok is None:
        result["reason"] = detail
        result["detail"] = detail
    elif ok:
        result["has_form"] = True
        result["has_url_field"] = True
        result["reason"] = "OK"
        result["detail"] = detail
        if stype in BLOG_COMMENT_TYPES:
            result["decision"] = "worth_one"
        else:
            result["decision"] = "report_only"
    else:
        result["reason"] = detail
        result["detail"] = detail
        if stype in BLOG_COMMENT_TYPES and is_hard_worth_zero_reason(detail):
            result["decision"] = "worth_zero"

    return result


def main():
    parser = argparse.ArgumentParser(description="评估所有 worth=NULL 站点（使用 CloakBrowser）")
    parser.add_argument("--type", help="只处理指定类型 (如 blog_comment)")
    parser.add_argument("--limit", type=int, help="最多处理多少个站点")
    parser.add_argument("--apply", action="store_true", help="应用结果到数据库")
    parser.add_argument("--resume", action="store_true", help="从上次进度续跑")
    parser.add_argument("--report", default="evaluate_worth_cloak_report.md", help="报告输出路径")
    args = parser.parse_args()

    migrate_database(DB_PATH)

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

    print("🚀 启动 CloakBrowser ...")
    browser = launch(headless=True, stealth_args=True)
    print("✅ CloakBrowser 已启动\n")

    results = {"worth_zero": [], "worth_one": [], "report_only": [], "keep_null": []}

    total = len(sites)
    for i, (sid, url, stype) in enumerate(pending, 1):
        global_seq = len(processed_ids) + i
        prefix = f"[{global_seq}/{total}]"
        url_short = url[:70]
        print(f"{prefix} ({stype}) {url_short}", end=" ... ", flush=True)

        context = browser.new_context()
        page = context.new_page()

        try:
            r = evaluate_site(page, sid, url, stype)
        finally:
            page.close()
            context.close()

        if r["decision"] == "worth_zero":
            print(f"❌ worth=0: {r['reason']}")
            if args.apply:
                mark_site_worth_zero(sid, r["reason"])
        elif r["decision"] == "worth_one":
            print(f"✅ worth=1")
            if args.apply:
                mark_site_worth_one(sid)
        elif r["decision"] == "report_only":
            print(f"⚠️ 有表单仅报告: {r['detail']}")
        else:
            print(f"🔍 保留 NULL: {r['reason']}")

        results[r["decision"]].append(r)

        processed_ids.add(sid)
        progress["processed"] = list(processed_ids)
        save_progress(progress)

        time.sleep(0.3)

    browser.close()

    print()
    print("=" * 70)
    print("📊 评估结果汇总")
    print(f"   总处理: {len(pending)}")
    print(f"   ❌ 硬障碍 → worth=0: {len(results['worth_zero'])}")
    print(f"   ✅ 确认有表单 (blog_comment) → worth=1: {len(results['worth_one'])}")
    print(f"   ⚠️ 有表单 (其他类型, 仅报告): {len(results['report_only'])}")
    print(f"   🔍 保留 NULL (待复查): {len(results['keep_null'])}")
    print()

    report_lines = []
    report_lines.append(f"# evaluate_worth_cloak 评估报告")
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

    if not args.apply:
        print("\n💡 要应用结果到数据库，加 --apply 参数")


if __name__ == "__main__":
    main()
