#!/usr/bin/env python3
"""
批量分析 22 个表单提交站点的表单结构。
使用 CloakBrowser (headless+stealth) 打开每个页面，提取表单字段、iframe 嵌入等信息。
每 5 个一批，避免资源耗尽。
"""

import json
import sys
import time
import traceback

from cloakbrowser import launch
from playwright.sync_api import TimeoutError as PwTimeout, Error as PwError

SITES = [
    (19, "https://theresanaiforthat.com/launch/"),
    (63, "https://www.01webdirectory.com/frmpresubmit.aspx"),
    (69, "https://www.63243.com/about/add.html"),
    (78, "https://library.phygital.plus/tool-submission"),
    (106, "https://www.allstatesusadirectory.com/submit.php"),
    (109, "https://apprater.net/add/"),
    (113, "https://bufferapps.com/beta-listing/new"),
    (115, "https://changelog.com/news/submit"),
    (136, "https://www.futuretools.io/submit-a-tool"),
    (143, "https://www.insidr.ai/submit-tools/"),
    (173, "https://startupcollections.com/submit-product/"),
    (177, "https://www.submit.biz/"),
    (178, "https://www.superaitools.io/submit-a-tool"),
    (181, "https://tap4.ai/cn/submit"),
    (203, "https://unmatchedstyle.com/submit"),
    (204, "https://viesearch.com/submit"),
    (225, "http://www.fwol.cn/infos_add.php"),
    (229, "https://tigg.cc/share"),
    (231, "https://www.yjpoo.com/submit-ai-tool/"),
    (232, "https://www.aiheron.com/promote"),
    (234, "https://www.hhlink.com/%E6%8F%90%E4%BA%A4%E6%96%B0%E7%BD%91%E7%AB%99"),
    (240, "https://lbbai.com/contribute"),
]

EXTRACT_JS = """
() => {
    const results = {};

    // Page info
    results.pageTitle = document.title || '';
    results.pageURL = window.location.href || '';

    // Check for iframe-based embedded forms
    const iframes = document.querySelectorAll('iframe');
    results.iframes = Array.from(iframes).map(f => ({
        src: (f.src || '').slice(0, 120),
        id: f.id || '',
        className: f.className || '',
        width: f.getAttribute('width') || '',
        height: f.getAttribute('height') || '',
    }));

    // Detect known form platforms
    const formPlatforms = [];
    const fpSet = new Set();
    const knownPlatforms = [
        { key: 'typeform', patterns: ['typeform'] },
        { key: 'airtable', patterns: ['airtable'] },
        { key: 'google_forms', patterns: ['google.com/forms', 'googleapis.com/forms', 'docs.google.com/forms'] },
        { key: 'notion', patterns: ['notion.so', 'notion.site'] },
        { key: 'tally', patterns: ['tally.so'] },
        { key: 'jotform', patterns: ['jotform', 'jotformeu'] },
        { key: 'formspree', patterns: ['formspree'] },
        { key: 'paperform', patterns: ['paperform'] },
        { key: 'cognitoforms', patterns: ['cognitoforms'] },
        { key: 'wufoo', patterns: ['wufoo'] },
        { key: 'hubspot', patterns: ['hubspot'] },
        { key: 'mailchimp', patterns: ['mailchimp'] },
        { key: 'gravityforms', patterns: ['gravityforms', 'gf_(?!.*email)'] },
        { key: 'contactform7', patterns: ['contactform7', 'wpcf7'] },
    ];
    for (const f of iframes) {
        const src = (f.src || '').toLowerCase();
        for (const p of knownPlatforms) {
            if (p.patterns.some(pat => src.includes(pat))) {
                if (!fpSet.has(p.key)) {
                    fpSet.add(p.key);
                    formPlatforms.push(p.key);
                }
            }
        }
    }
    // Also check page text for embedded form mentions
    const bodyText = document.body.innerText.toLowerCase();
    const mentionedPlatforms = [
        { key: 'typeform', patterns: ['typeform'] },
        { key: 'airtable', patterns: ['airtable'] },
        { key: 'google_forms', patterns: ['google form'] },
        { key: 'tally', patterns: ['tally.so'] },
        { key: 'jotform', patterns: ['jotform'] },
    ];
    for (const p of mentionedPlatforms) {
        if (p.patterns.some(pat => bodyText.includes(pat))) {
            if (!fpSet.has(p.key)) {
                fpSet.add(p.key);
                formPlatforms.push(p.key + '_mentioned');
            }
        }
    }
    results.formPlatforms = formPlatforms;
    results.hasFormInText = /form|submit|application|apply/i.test(bodyText);

    // Extract all <form> elements
    const forms = document.querySelectorAll('form');
    results.formCount = forms.length;
    results.forms = Array.from(forms).map(form => {
        const isHidden = form.offsetParent === null;
        const rect = form.getBoundingClientRect();
        const fields = [];
        // Inputs, textareas, selects
        const formEls = form.querySelectorAll('input, textarea, select');
        for (const el of formEls) {
            const labelEl = el.id ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`) : null;
            const parentLabel = el.closest('label');
            const ariaLabel = el.getAttribute('aria-label') || '';
            let labelText = '';
            if (labelEl) labelText = labelEl.textContent.trim();
            else if (parentLabel) labelText = parentLabel.textContent.trim().replace(el.value || '', '').trim();
            else if (ariaLabel) labelText = ariaLabel;

            fields.push({
                tag: el.tagName.toLowerCase(),
                name: el.name || '',
                id: el.id || '',
                type: el.type || '',
                placeholder: el.placeholder || '',
                required: el.hasAttribute('required'),
                disabled: el.disabled,
                label: labelText,
                className: (el.className || '').slice(0, 60),
                autocomplete: el.getAttribute('autocomplete') || '',
            });
        }

        // Submit buttons
        const buttons = form.querySelectorAll('button[type=submit], button:not([type]):not([type=button]):not([type=reset]), input[type=submit], input[type=image]');
        for (const btn of buttons) {
            fields.push({
                tag: btn.tagName.toLowerCase(),
                name: btn.name || '',
                id: btn.id || '',
                type: btn.type || 'submit',
                placeholder: '',
                required: false,
                disabled: btn.disabled,
                label: btn.value || btn.textContent.trim() || '',
                className: (btn.className || '').slice(0, 60),
                autocomplete: '',
            });
        }

        return {
            id: form.id || '',
            name: form.name || '',
            action: (form.action || '').slice(0, 120),
            method: (form.method || 'get').toLowerCase(),
            isVisible: !isHidden,
            rect: isHidden ? null : { top: Math.round(rect.top), left: Math.round(rect.left), width: Math.round(rect.width), height: Math.round(rect.height) },
            fieldCount: fields.length,
            fields: fields,
        };
    });

    // Look for common form containers that might have forms loaded via JS
    const formContainers = document.querySelectorAll('[class*="form" i], [id*="form" i], [class*="submit" i], [id*="submit" i]');
    results.formContainerCount = formContainers.length;

    // Check if page has a URL/Website input anywhere
    const urlInputs = document.querySelectorAll('input[type="url"], input[name*="url" i], input[id*="url" i], input[name*="website" i], input[id*="website" i], input[placeholder*="url" i], input[placeholder*="website" i]');
    results.hasUrlInput = urlInputs.length > 0;
    results.urlInputs = Array.from(urlInputs).map(el => ({
        name: el.name || '',
        id: el.id || '',
        placeholder: el.placeholder || '',
        type: el.type || '',
    }));

    return results;
}
"""


def analyze_site(browser, sid, url):
    """Analyze a single site and return structured results."""
    result = {
        "id": sid,
        "url": url,
        "success": False,
        "error": "",
        "pageTitle": "",
        "pageURL": "",
        "accessible": False,
        "formCount": 0,
        "forms": [],
        "iframes": [],
        "formPlatforms": [],
        "hasUrlInput": False,
        "urlInputs": [],
    }

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
    )
    page = context.new_page()

    try:
        response = page.goto(url, timeout=30000, wait_until="commit")
        status = response.status if response else 0
        result["httpStatus"] = status

        # Wait for JS render
        page.wait_for_timeout(3000)

        # Check if we got a real page
        if "about:blank" in page.url:
            result["error"] = "Redirected to about:blank (anti-bot)"
            context.close()
            return result

        result["accessible"] = True

        # Scroll to bottom to trigger lazy loading
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            # Scroll back to top
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
        except Exception:
            pass

        # Extract all form data
        try:
            data = page.evaluate(EXTRACT_JS)
            if isinstance(data, dict):
                result["pageTitle"] = data.get("pageTitle", "")
                result["pageURL"] = data.get("pageURL", "")
                result["formCount"] = data.get("formCount", 0)
                result["forms"] = data.get("forms", [])
                result["iframes"] = data.get("iframes", [])
                result["formPlatforms"] = data.get("formPlatforms", [])
                result["hasUrlInput"] = data.get("hasUrlInput", False)
                result["urlInputs"] = data.get("urlInputs", [])
                result["hasFormInText"] = data.get("hasFormInText", False)
                result["formContainerCount"] = data.get("formContainerCount", 0)
        except Exception as e:
            result["error"] = f"JS eval failed: {str(e)[:80]}"

        result["success"] = True

    except PwTimeout:
        result["error"] = "Navigation timeout"
    except PwError as e:
        msg = str(e).lower()
        if "timeout" in msg:
            result["error"] = "Navigation timeout"
        elif "ssl" in msg or "certificate" in msg:
            result["error"] = "SSL error"
        elif "dns" in msg or "name_not_resolved" in msg:
            result["error"] = "DNS resolution failed"
        elif "connection_refused" in msg or "connection_closed" in msg:
            result["error"] = "Connection refused/closed"
        elif "404" in msg or "not found" in msg:
            result["error"] = "404 not found"
        else:
            result["error"] = str(e)[:100]
    except Exception as e:
        result["error"] = f"Unexpected: {str(e)[:100]}"

    context.close()
    return result


def batch_analyze(sites, batch_size=5):
    """Analyze sites in batches."""
    all_results = []
    total = len(sites)

    print(f"🚀 Launching CloakBrowser ...", file=sys.stderr)
    browser = launch(headless=True, stealth_args=True)
    print(f"✅ CloakBrowser ready\n", file=sys.stderr)

    try:
        for batch_start in range(0, total, batch_size):
            batch = sites[batch_start:batch_start + batch_size]
            batch_num = batch_start // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"📦 Batch {batch_num}/{total_batches} ({len(batch)} sites)", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)

            for sid, url in batch:
                print(f"  🔍 [{sid}] {url[:80]} ...", file=sys.stderr, end=" ")
                sys.stderr.flush()

                result = analyze_site(browser, sid, url)

                if result["success"]:
                    fc = result.get("formCount", 0)
                    ui = result.get("hasUrlInput", False)
                    fp = result.get("formPlatforms", [])
                    print(f"OK (forms={fc}, urlInput={ui}, platforms={fp})", file=sys.stderr)
                else:
                    print(f"FAIL: {result['error']}", file=sys.stderr)

                all_results.append(result)
                time.sleep(0.5)  # small delay between sites

    finally:
        browser.close()
        print(f"\n✅ CloakBrowser closed", file=sys.stderr)

    return all_results


def compact_output(results):
    """Return a compact JSON representation."""
    output = []
    for r in results:
        site = {
            "id": r["id"],
            "url": r["url"],
            "title": r.get("pageTitle", ""),
            "httpStatus": r.get("httpStatus", 0),
            "success": r["success"],
            "accessible": r["accessible"],
            "error": r.get("error", ""),
            "formCount": r.get("formCount", 0),
            "hasUrlInput": r.get("hasUrlInput", False),
            "formPlatforms": r.get("formPlatforms", []),
            "iframeCount": len(r.get("iframes", [])),
        }

        # Compact form info
        if r.get("forms"):
            forms_compact = []
            for f in r["forms"]:
                form_entry = {
                    "id": f["id"],
                    "action": f["action"][:80],
                    "method": f["method"],
                    "visible": f["isVisible"],
                    "fields": [],
                }
                for field in f["fields"]:
                    form_entry["fields"].append({
                        "tag": field["tag"],
                        "name": field["name"],
                        "type": field["type"],
                        "placeholder": field["placeholder"],
                        "required": field["required"],
                        "label": field["label"],
                    })
                forms_compact.append(form_entry)
            site["forms"] = forms_compact
        else:
            site["forms"] = []

        # Iframe info
        if r.get("iframes"):
            site["iframes"] = [
                {"src": ifr["src"][:80], "id": ifr["id"]}
                for ifr in r["iframes"]
                if ifr.get("src")
            ]

        # URL inputs
        if r.get("urlInputs"):
            site["urlInputs"] = r["urlInputs"]

        output.append(site)

    return json.dumps(output, ensure_ascii=False, indent=2)


def main():
    print(f"📋 Total sites to analyze: {len(SITES)}", file=sys.stderr)
    print(f"📦 Batch size: 5", file=sys.stderr)
    print(file=sys.stderr)

    results = batch_analyze(SITES, batch_size=5)

    # Print compact JSON to stdout
    print(compact_output(results))


if __name__ == "__main__":
    main()
