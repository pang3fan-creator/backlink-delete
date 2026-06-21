#!/usr/bin/env python3
"""
通用 form 类型外链提交脚本（CloakBrowser）
用于非 WordPress 的目录/工具提交流通，配置驱动，按站点逐一提交。

用法：
  # dry-run 预览
  python3 backlink_form_submit.py --project extractkeywords.com \\
    --submit-url "https://extractkeywords.com" --dry-run

  # 正式提交
  python3 backlink_form_submit.py --project extractkeywords.com \\
    --submit-url "https://extractkeywords.com" --limit 5

  # 单个站点
  python3 backlink_form_submit.py --project extractkeywords.com \\
    --submit-url "https://extractkeywords.com" --site-id 204
"""

import argparse
import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from backlink_common import (
    DB_PATH,
    LOG_FILE,
    is_hard_worth_zero_reason,
    migrate_database,
)
from cloakbrowser import launch
from playwright.sync_api import TimeoutError as PwTimeout, Error as PwError

ROOT = Path(__file__).parent

DEFAULT_NAME = "Stefan M."
DEFAULT_EMAIL = "pang3fan@gmail.com"

# --- 站点配置 ---
# 每个站点定义：url, 字段映射, 提交按钮, 成功检测方式
# fields: [(识别方式, 识别值, 字段类型, 填充值来源), ...]
#   识别方式: 'name' | 'selector' | 'placeholder'
#   字段类型: 'text' | 'url' | 'email' | 'textarea' | 'select'
#   填充值来源: 'name' | 'email' | 'submit_url' | 'tool_name' | 'description' | 'tags'
# submit: {方式, 值}
#   方式: 'text' | 'selector' | 'css'
# success: {方式, 值列表}

SITE_CONFIGS = {
    # --- A 档：自动可提交 ---
    78: {
        'url': 'https://library.phygital.plus/tool-submission',
        'type': 'standard',
        'fields': [
            ('placeholder', 'Link to the tool', 'url', 'submit_url'),
            ('placeholder', 'Describe the tool', 'textarea', 'description'),
        ],
        'submit': {'text': 'Submit'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
    },
    106: {
        'url': 'https://www.allstatesusadirectory.com/submit.php',
        'type': 'standard',
        'fields': [
            ('name', 'TITLE', 'text', 'tool_name'),
            ('name', 'URL', 'url', 'submit_url'),
            ('name', 'DESCRIPTION', 'textarea', 'description'),
            ('name', 'OWNER_NAME', 'text', 'name'),
            ('name', 'OWNER_EMAIL', 'email', 'email'),
            ('name', 'META_KEYWORDS', 'text', 'tags'),
            ('name', 'CATEGORY_ID', 'select', ''),
        ],
        'submit': {'name': 'submit'},
        'success': {'indicators': ['thank', 'submit', 'success', 'added']},
        'notes': '有 CAPTCHA 字段，需人工处理验证码',
    },
    109: {
        'url': 'https://apprater.net/add/',
        'type': 'usp',
        'fields': [
            ('name', 'user-submitted-name', 'text', 'name'),
            ('name', 'user-submitted-email', 'email', 'email'),
            ('name', 'user-submitted-title', 'text', 'tool_name'),
            ('name', 'user-submitted-url[]', 'url', 'submit_url'),
            ('name', 'user-submitted-content', 'textarea', 'description'),
        ],
        'submit': {'name': 'user-submitted-post'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
    },
    113: {
        'url': 'https://bufferapps.com/beta-listing/new',
        'type': 'noname',
        'fields': [
            ('placeholder', 'Product Name', 'text', 'tool_name'),
            ('placeholder', 'Product tagline', 'text', 'description'),
            ('selector', 'input[placeholder*="https://www.website.com"]', 'url', 'submit_url'),
        ],
        'submit': {'text': 'Submit'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
        'notes': '字段无 name 属性，通过 placeholder 定位',
    },
    115: {
        'url': 'https://changelog.com/news/submit',
        'type': 'standard',
        'fields': [
            ('name', 'news_item[url]', 'url', 'submit_url'),
            ('name', 'news_item[headline]', 'text', 'tool_name'),
            ('name', 'news_item[story]', 'textarea', 'description'),
        ],
        'submit': {'text': 'Submit'},
        'success': {'indicators': ['thanks', 'your story has been submitted']},
        'notes': '含 CSRF token，浏览器自动处理',
    },
    136: {
        'url': 'https://www.futuretools.io/submit-a-tool',
        'type': 'standard',
        'fields': [
            ('name', 'tool_name', 'text', 'tool_name'),
            ('name', 'tool_url', 'url', 'submit_url'),
            ('name', 'description', 'textarea', 'description'),
            ('name', 'submitter_name', 'text', 'name'),
            ('name', 'submitter_email', 'email', 'email'),
        ],
        'submit': {'text': 'Submit Tool'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
        'notes': '有 Cloudflare Turnstile，尝试提交，失败则需验证码',
    },
    143: {
        'url': 'https://www.insidr.ai/submit-tools/',
        'type': 'elementor',
        'fields': [
            ('name', 'form_fields[name]', 'url', 'submit_url'),
            ('name', 'form_fields[email]', 'text', 'tool_name'),
            ('name', 'form_fields[message]', 'textarea', 'description'),
        ],
        'submit': {'selector': 'button[type=submit]'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
        'notes': 'form_fields[name] 实际是链接输入框',
    },
    173: {
        'url': 'https://startupcollections.com/submit-product/',
        'type': 'standard',
        'fields': [
            ('name', 'name', 'text', 'tool_name'),
            ('name', 'website', 'url', 'submit_url'),
            ('name', 'content', 'textarea', 'description'),
            ('name', 'submitter_name', 'text', 'name'),
            ('name', 'submitter_email', 'email', 'email'),
        ],
        'submit': {'text': 'Submit'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
    },
    178: {
        'url': 'https://www.superaitools.io/submit-a-tool',
        'type': 'gravity',
        'fields': [
            ('placeholder', 'Your Name', 'text', 'name'),
            ('placeholder', 'Your Business Email', 'email', 'email'),
            ('placeholder', 'Tool Name', 'text', 'tool_name'),
            ('placeholder', 'Tool link', 'url', 'submit_url'),
            ('placeholder', 'Tool Tags', 'text', 'tags'),
            ('placeholder', 'Describe your product', 'textarea', 'description'),
        ],
        'submit': {'text': 'Submit'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
    },
    203: {
        'url': 'https://unmatchedstyle.com/submit',
        'type': 'wpforms',
        'fields': [
            ('name', 'wpforms[fields][2][first]', 'text', 'name'),
            ('name', 'wpforms[fields][3]', 'email', 'email'),
            ('name', 'wpforms[fields][4]', 'textarea', 'description'),
            ('name', 'wpforms[fields][6]', 'text', 'tool_name'),
            ('name', 'wpforms[fields][14]', 'url', 'submit_url'),
        ],
        'submit': {'text': 'Submit'},
        'success': {'indicators': ['thanks', 'submitted', 'success']},
        'notes': '表单字段较多，有文件上传字段可跳过',
    },
    204: {
        'url': 'https://viesearch.com/submit',
        'type': 'standard',
        'fields': [
            ('name', 'url', 'url', 'submit_url'),
            ('name', 'title', 'text', 'tool_name'),
            ('name', 'description', 'textarea', 'description'),
            ('name', 'email', 'email', 'email'),
        ],
        'submit': {'selector': '#submit-form button[type=submit]'},
        'success': {'indicators': ['submitted', 'success', 'thank you']},
    },
    229: {
        'url': 'https://tigg.cc/share',
        'type': 'noname',
        'fields': [
            ('selector', 'input[placeholder*="https://"]', 'url', 'submit_url'),
            ('selector', 'input[placeholder*="如："]', 'text', 'tool_name'),
            ('selector', 'textarea[placeholder*="详细描述"]', 'textarea', 'description'),
            ('selector', 'input[placeholder*="昵称"]', 'text', 'name'),
        ],
        'submit': {'text': '提交'},
        'success': {'indicators': ['谢谢', '成功', 'thanks']},
    },
    240: {
        'url': 'https://lbbai.com/contribute',
        'type': 'standard',
        'fields': [
            ('name', 'post_title', 'text', 'tool_name'),
            ('name', 'link', 'url', 'submit_url'),
            ('name', 'describe', 'textarea', 'description'),
            ('name', 'guest_info[name]', 'text', 'name'),
            ('name', 'guest_info[contact]', 'text', 'email'),
        ],
        'submit': {'text': '提交'},
        'success': {'indicators': ['谢谢', '成功', 'thanks']},
    },

    # --- B 档：需适配 ---
    63: {
        'url': 'https://www.01webdirectory.com/frmpresubmit.aspx',
        'type': 'aspnet',
        'fields': [],
        'submit': {'text': 'Site Submission'},
        'success': {'indicators': ['success', 'submitted', 'thank']},
        'notes': 'ASP.NET 表单，需选分类后按钮才出现',
    },
    231: {
        'url': 'https://www.yjpoo.com/submit-ai-tool/',
        'type': 'standard',
        'fields': [
            ('name', 'attr_28', 'text', 'tool_name'),
            ('name', 'attr_30', 'url', 'submit_url'),
            ('name', 'attr_38', 'textarea', 'description'),
            ('name', 'username', 'text', 'name'),
        ],
        'submit': {'name': 'submit'},
        'success': {'indicators': ['thanks', '提交成功', 'success']},
        'notes': '含用户名/密码字段，可能需登录',
    },
}

# --- 项目描述模板 ---
PROJECT_DESCRIPTIONS = {
    'extractkeywords.com': 'Free online keyword extraction tool for SEO professionals and content creators.',
    'heicpdf.to': 'Free online HEIC to PDF converter - convert iPhone photos to PDF instantly.',
    'tryschedule.com': 'Free online schedule builder and planner for better time management.',
}


def load_project_name(project: str) -> str:
    """从 project-config.json 提取工具名"""
    try:
        cfg = json.loads((ROOT / 'project-config.json').read_text())
        for key, val in cfg.get('projects', {}).items():
            if val.get('domain') == project or val.get('name') == project:
                return val.get('name', project)
    except Exception:
        pass
    return project.split('.')[0] if '.' in project else project


def build_field_values(project: str, submit_url: str, name: str, email: str, description: str) -> dict:
    """构建填充值字典"""
    tool_name = load_project_name(project)
    tags = ''
    try:
        cfg = json.loads((ROOT / 'project-config.json').read_text())
        for val in cfg.get('projects', {}).values():
            if val.get('domain') == project or val.get('name') == project:
                tags = ', '.join(val.get('tags', []))
                break
    except Exception:
        pass
    if not description:
        description = PROJECT_DESCRIPTIONS.get(project, f'A free online tool at {submit_url}')
    return {
        'name': name,
        'email': email,
        'submit_url': submit_url,
        'tool_name': tool_name,
        'description': description,
        'tags': tags,
    }


def escape_css(value: str) -> str:
    """转义 CSS 选择器中的特殊字符"""
    return value.replace("'", "\\'").replace('"', '\\"')


# --- 核心引擎 ---

def wait_for_page(page):
    """页面加载后等待 JS 渲染"""
    try:
        page.wait_for_timeout(3000)
    except Exception:
        pass


def scroll_to_bottom(page):
    """滚动到底部"""
    try:
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(1000)
    except Exception:
        pass


def analyze_page_fields(page) -> list[dict]:
    """检测页面上的所有表单字段（用于 dry-run 输出）"""
    try:
        fields = page.evaluate("""
            () => {
                const forms = document.querySelectorAll('form');
                const results = [];
                for (const form of forms) {
                    const isHidden = form.offsetParent === null;
                    const els = form.querySelectorAll('input:not([type=hidden]):not([type=submit]), textarea, select');
                    for (const el of els) {
                        const rect = el.getBoundingClientRect();
                        const label = form.querySelector(`label[for="${el.id}"]`);
                        const labelText = label ? label.textContent.trim() : '';
                        results.push({
                            formId: form.id || '',
                            name: el.name || '',
                            id: el.id || '',
                            type: el.type || el.tagName.toLowerCase(),
                            placeholder: el.placeholder || '',
                            label: labelText,
                            required: el.required || false,
                            visible: rect.width > 0 && rect.height > 0 && !isHidden,
                        });
                    }
                }
                return results;
            }
        """)
        return fields
    except Exception as e:
        return [{'error': str(e)[:80]}]


def q(v: str) -> str:
    """Quote a value for CSS attribute selector (no CSS escaping needed inside quotes)."""
    return v.replace('"', '\\"')


def fill_field_by_strategy(page, strategy: str, selector: str, value: str, field_type: str) -> bool:
    """按策略定位并填写字段"""
    if not value:
        return False
    try:
        if strategy == 'name':
            sel = f'[name="{q(selector)}"]'
            if field_type in ('textarea',):
                sel = f'textarea{sel}'
            elif field_type in ('select', 'select-one'):
                page.select_option(sel, value)
                return True
            else:
                sel = f'input{sel}'
            page.fill(sel, value)
            return True
        elif strategy == 'selector':
            page.fill(selector, value)
            return True
        elif strategy == 'placeholder':
            sel = f'[placeholder*="{q(selector)}"]'
            inp = page.query_selector(f'input{sel}')
            if inp:
                inp.fill(value)
                return True
            ta = page.query_selector(f'textarea{sel}')
            if ta:
                ta.fill(value)
                return True
            return False
    except Exception:
        return False


def click_submit_button(page, config: dict) -> bool:
    """定位并点击提交按钮"""
    submit = config.get('submit', {})
    try:
        if 'text' in submit:
            text = submit['text']
            try:
                btn = page.query_selector(f'button:has-text("{escape_css(text)}")')
                if btn:
                    btn.click()
                    return True
            except Exception:
                pass
            try:
                btn = page.query_selector(f'input[type=submit][value="{escape_css(text)}"], input[type=button][value="{escape_css(text)}"]')
                if btn:
                    btn.click()
                    return True
            except Exception:
                pass
        if 'name' in submit:
            name = submit['name']
            for sel in [f'[name="{escape_css(name)}"]', f'#{escape_css(name)}']:
                try:
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        return True
                except Exception:
                    pass
        if 'selector' in submit:
            el = page.query_selector(submit['selector'])
            if el:
                el.click()
                return True
        # Fallback: any submit button
        for sel in ['button[type=submit]', 'input[type=submit]', 'button:has-text("Submit")', 'button:has-text("提交")']:
            try:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def detect_result(page, config: dict, original_url: str) -> dict:
    """检测提交结果"""
    try:
        page.wait_for_timeout(3000)
    except Exception:
        pass

    current_url = page.url
    success_indicators = config.get('success', {}).get('indicators', [])
    body_text = ''
    try:
        body_text = page.inner_text('body').lower()
    except Exception:
        pass

    result = {'found': False, 'status': '失败', 'reason': '', 'comment_id': ''}

    # 检测 URL 变化（成功提交后通常跳转）
    if current_url != original_url:
        result['found'] = True
        result['reason'] = f'url_changed: {current_url[:80]}'
        result['status'] = '已提交'
        return result

    # 检测成功指示文字
    for indicator in success_indicators:
        if indicator.lower() in body_text:
            result['found'] = True
            result['reason'] = f'success_text: {indicator}'
            result['status'] = '已提交'
            return result

    # 通用成功关键词
    generic_success = ['thank you', 'thanks', 'submitted', 'success', '成功', '谢谢', '提交成功', '已提交']
    for word in generic_success:
        if word.lower() in body_text:
            result['found'] = True
            result['reason'] = f'success_text: {word}'
            result['status'] = '已提交'
            return result

    # 检测错误
    generic_error = ['error', 'invalid', 'wrong', 'failed', '错误', '验证码错误', '请输入验证码']
    for word in generic_error:
        if word.lower() in body_text:
            result['found'] = False
            result['reason'] = f'error_text: {word}'
            result['status'] = '失败'
            return result

    # 检测是否需要验证码
    capcha_keywords = ['captcha', 'recaptcha', 'verification code', '验证码', 'turnstile']
    for word in capcha_keywords:
        if word.lower() in body_text:
            result['found'] = False
            result['reason'] = f'captcha_detected: {word}'
            result['status'] = '需验证码'
            return result

    # 无明确结果
    result['found'] = False
    result['reason'] = 'no_detectable_result'
    result['status'] = '待确认'
    return result


def save_submission(site_id: int, project: str, status: str, notes: str = '',
                    submit_url: str = '', target_url: str = '', comment_text: str = '',
                    comment_id: str = '', result_reason: str = ''):
    """保存提交记录到数据库"""
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('''
        INSERT INTO submissions (
            site_id, project_name, status, notes, updated_at,
            submit_url, target_url, comment_text, comment_id, result_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(site_id, project_name) DO UPDATE SET
            status=?, notes=?, updated_at=?,
            submit_url=?, target_url=?, comment_text=?, comment_id=?, result_reason=?
    ''', (
        site_id, project, status, notes, now_ts,
        submit_url, target_url, comment_text, comment_id, result_reason,
        status, notes, now_ts,
        submit_url, target_url, comment_text, comment_id, result_reason,
    ))
    conn.commit()
    conn.close()
    # 审计日志
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = f"=== {now_ts} ===\n站点ID: {site_id}\n项目: {project}\n提交URL: {submit_url}\n状态: {status}\n结果: {result_reason}"
    if notes:
        entry += f"\n备注: {notes}"
    entry += "\n\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def update_worth(site_id: int, success: bool, reason: str):
    """更新站点 worth 状态"""
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        if success:
            conn.execute(
                'UPDATE sites SET worth_submitting = 1, skip_reason = NULL, consecutive_failures = 0 WHERE id = ?',
                (site_id,),
            )
        elif is_hard_worth_zero_reason(reason):
            conn.execute(
                'UPDATE sites SET worth_submitting = 0, skip_reason = ?, consecutive_failures = COALESCE(consecutive_failures, 0) + 1 WHERE id = ?',
                (reason, site_id),
            )
        else:
            conn.execute(
                'UPDATE sites SET consecutive_failures = COALESCE(consecutive_failures, 0) + 1 WHERE id = ?',
                (site_id,),
            )
        conn.commit()
    finally:
        conn.close()


def submit_site(browser, site_id: int, config: dict,
                project: str, submit_url: str, name: str, email: str,
                description: str, dry_run: bool = False) -> dict:
    """提交单个站点"""
    result = {
        'site_id': site_id,
        'url': config['url'],
        'success': False,
        'status': '失败',
        'error': '',
        'reason': '',
        'dry_run': dry_run,
    }

    values = build_field_values(project, submit_url, name, email, description)

    if dry_run:
        print(f"\n{'='*60}")
        print(f"[DRY-RUN] ID {site_id}: {config['url']}")
        try:
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(20000)
            resp = page.goto(config['url'], wait_until='commit')
            wait_for_page(page)
            scroll_to_bottom(page)

            page_ok = resp and resp.ok
            fields = analyze_page_fields(page)
            config_fields = config.get('fields', [])

            print(f"  页面可达: {'✅' if page_ok else '❌'} (HTTP {resp.status if resp else 'N/A'})")
            if page.title():
                print(f"  标题: {page.title()[:80]}")
            print(f"  检测到表单字段: {len(fields)}")
            for f in fields[:15]:
                val = values.get(f['name']) or ''
                matched = any(f['name'] == cf[1] for cf in config_fields)
                matched = matched or any(cf[1].lower() in f['placeholder'].lower() for cf in config_fields if cf[0] == 'placeholder')
                matched = matched or any(f['placeholder'] and cf[1].lower() in f['placeholder'].lower() for cf in config_fields)
                pfix = '✅' if matched else '  '
                show_val = f" → '{val[:40]}'" if matched and val else ''
                print(f"  {pfix} [{f['type']}] name={f['name']} placeholder=\"{f['placeholder']}\"{show_val}")

            if config.get('notes'):
                print(f"  备注: {config['notes']}")

            unfielded = config.get('fields', [])
            fielded_names = set(f['name'] for f in fields)
            for cf in config_fields:
                if cf[0] == 'name' and cf[1] not in fielded_names:
                    print(f"  ⚠️ 配置字段 '{cf[1]}' 未在页面检测到")
                elif cf[0] == 'placeholder':
                    found = any(cf[1].lower() in f.get('placeholder', '').lower() for f in fields)
                    if not found:
                        print(f"  ⚠️ 配置占位符 '{cf[1]}' 未匹配到页面字段")

            submit_cfg = config.get('submit', {})
            print(f"  提交按钮: {submit_cfg}")
            print(f"  预估成功率: {'高' if len(fields) >= len(config_fields) else '中' if len(fields) > 0 else '低'}")

            page.close()
            context.close()
        except Exception as e:
            print(f"  ❌ 页面打开失败: {type(e).__name__}: {str(e)[:80]}")
        result['success'] = True
        result['status'] = 'dry-run OK'
        return result

    # --- 正式提交 ---
    print(f"\n{'='*60}")
    print(f"[SUBMIT] ID {site_id}: {config['url']}")

    try:
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(25000)
        resp = page.goto(config['url'], wait_until='commit')
        wait_for_page(page)
        scroll_to_bottom(page)

        # 检查页面是否可达
        if not resp or not resp.ok:
            result['error'] = f'HTTP {resp.status if resp else "N/A"}'
            result['status'] = '已失效'
            print(f"  ❌ 页面不可达: {result['error']}")
            page.close()
            context.close()
            return result

        # 填写字段
        filled_count = 0
        for strategy, selector, field_type, value_key in config.get('fields', []):
            value = values.get(value_key, '')
            if not value:
                continue
            ok = fill_field_by_strategy(page, strategy, selector, value, field_type)
            if ok:
                filled_count += 1

        if filled_count == 0 and config.get('fields'):
            result['error'] = '无法填写任何字段'
            result['status'] = '失败'
            print(f"  ❌ {result['error']}")
            page.close()
            context.close()
            save_submission(site_id, project, result['status'],
                          notes=result['error'], target_url=config['url'])
            return result

        print(f"  ✓ 已填写 {filled_count}/{len(config.get('fields', []))} 个字段")

        # 点击提交
        clicked = click_submit_button(page, config)
        if not clicked:
            result['error'] = '找不到提交按钮'
            result['status'] = '失败'
            print(f"  ❌ {result['error']}")
            page.close()
            context.close()
            save_submission(site_id, project, result['status'],
                          notes=result['error'], target_url=config['url'])
            return result

        print(f"  ✓ 已点击提交按钮")

        # 检测结果
        original_url = page.url
        detect = detect_result(page, config, original_url)

        result['success'] = detect['found']
        result['status'] = detect['status']
        result['reason'] = detect['reason']

        if detect['found']:
            print(f"  ✅ 提交成功: {detect['reason']}")
        else:
            print(f"  {'⚠️' if detect['status'] == '待确认' else '❌'} {detect['status']}: {detect['reason']}")

        # 保存到数据库
        save_submission(
            site_id, project, detect['status'],
            notes=detect['reason'],
            submit_url=submit_url,
            target_url=config['url'],
            comment_text=description,
            result_reason=detect['reason'],
        )
        update_worth(site_id, detect['found'], detect['reason'])

        page.close()
        context.close()

    except PwTimeout as e:
        result['error'] = f'timeout: {str(e)[:80]}'
        result['status'] = '失败'
        print(f"  ❌ 超时: {str(e)[:80]}")
        save_submission(site_id, project, '失败',
                      notes=result['error'], target_url=config['url'])
    except PwError as e:
        result['error'] = str(e)[:120]
        msg = str(e).lower()
        if 'certificate' in msg or 'ssl' in msg or 'cert' in msg:
            result['status'] = '已失效'
        elif 'timeout' in msg:
            result['status'] = '失败'
        else:
            result['status'] = '失败'
        print(f"  ❌ 浏览器错误: {result['error'][:80]}")
        save_submission(site_id, project, result['status'],
                      notes=result['error'], target_url=config['url'])
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {str(e)[:120]}'
        result['status'] = '失败'
        print(f"  ❌ 异常: {result['error'][:80]}")
        try:
            save_submission(site_id, project, '失败',
                          notes=result['error'], target_url=config['url'])
        except Exception:
            pass

    return result


def load_site_url(site_id: int) -> Optional[str]:
    """从数据库获取站点 URL"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT site_url FROM sites WHERE id = ?', (site_id,))
        r = cur.fetchone()
        conn.close()
        return r[0] if r else None
    except Exception:
        return None


def get_pending_sites(project: str, site_type: str = 'form') -> list[tuple]:
    """获取待提交站点"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT s.id, s.site_url
        FROM sites s
        LEFT JOIN submissions sb ON s.id = sb.site_id AND sb.project_name = ?
        WHERE s.site_type = ? AND s.worth_submitting = 1 AND sb.id IS NULL
        ORDER BY s.id
    ''', (project, site_type))
    rows = cur.fetchall()
    conn.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description='通用 form 外链提交工具 (CloakBrowser)')
    parser.add_argument('--project', required=True, help='项目名称 (如 extractkeywords.com)')
    parser.add_argument('--submit-url', required=True, help='要提交的外链 URL')
    parser.add_argument('--site-id', type=int, help='指定单个站点 ID')
    parser.add_argument('--limit', type=int, help='最多提交多少个站点')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际提交')
    parser.add_argument('--name', default=DEFAULT_NAME, help=f'姓名 (默认: {DEFAULT_NAME})')
    parser.add_argument('--email', default=DEFAULT_EMAIL, help=f'邮箱 (默认: {DEFAULT_EMAIL})')
    parser.add_argument('--description', default='', help='描述文本 (覆盖默认)')
    parser.add_argument('--no-backup', action='store_true', help='跳过数据库备份')
    args = parser.parse_args()

    migrate_database(DB_PATH)

    # 备份
    if not args.dry_run and not args.no_backup:
        backup_dir = ROOT / 'backups'
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"backlinks-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
        shutil.copy2(DB_PATH, backup_path)
        print(f'💾 数据库备份: {backup_path}')

    # 确定待提交站点列表
    configured_ids = list(SITE_CONFIGS.keys())
    if args.site_id:
        site_ids = [args.site_id]
    elif args.dry_run:
        site_ids = configured_ids
    else:
        pending = get_pending_sites(args.project)
        configured_set = set(configured_ids)
        pending_ids = set(p[0] for p in pending if p[0] in configured_set)

        # 取配置中所有站点（包括尚未标记 worth=1 的）
        all_configured = set(configured_ids)
        # 优先用未提交的 worth=1 站点，不足时补充其他已配置站点
        already_submitted = set()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'SELECT site_id FROM submissions WHERE project_name = ?',
            (args.project,),
        )
        already_submitted = set(r[0] for r in cur.fetchall())
        conn.close()

        # 只重试失败的站点，跳过已成功的
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            'SELECT site_id, status FROM submissions WHERE project_name = ?',
            (args.project,),
        )
        skip_status = set()
        retry_ids = set()
        for sid, st in cur.fetchall():
            if st in ("需付费", "需验证码", "已提交", "待确认"):
                skip_status.add(sid)
            elif st == "失败":
                retry_ids.add(sid)
        conn.close()

        never_submitted = all_configured - already_submitted
        retry_configured = retry_ids & all_configured
        candidate = never_submitted | retry_configured
        if candidate:
            site_ids = sorted(candidate)
        else:
            print(f'⚠️ 所有配置站点已提交到 {args.project}')
            return

    if args.limit:
        site_ids = site_ids[:args.limit]

    if not site_ids:
        print('没有待提交的站点')
        return

    # 检查站点是否都在配置中
    configured = SITE_CONFIGS
    valid_sites = [(sid, configured[sid]) for sid in site_ids if sid in configured]
    unknown_sites = [sid for sid in site_ids if sid not in configured]
    if unknown_sites:
        print(f'⚠️ 以下站点无配置，跳过: {unknown_sites}')

    if not valid_sites:
        print('所有站点均无配置')
        return

    if args.dry_run:
        mode = 'dry-run (预览)'
    else:
        mode = f'submit → {args.project}'

    print(f'\n🔥 模式: {mode}')
    print(f'📋 待处理: {len(valid_sites)} 个站点')
    print(f'   project: {args.project}')
    print(f'   submit-url: {args.submit_url}')
    print(f'   name: {args.name}')
    print(f'   email: {args.email}')
    if args.description:
        print(f'   description: {args.description}')
    print()

    # 启动浏览器
    print('🚀 启动 CloakBrowser ...')
    try:
        browser = launch(headless=True, stealth_args=True)
        print('✅ CloakBrowser 已启动\n')
    except Exception as e:
        print(f'❌ 浏览器启动失败: {e}')
        sys.exit(1)

    results = []
    try:
        for i, (site_id, config) in enumerate(valid_sites, 1):
            r = submit_site(
                browser, site_id, config,
                args.project, args.submit_url,
                args.name, args.email,
                args.description or PROJECT_DESCRIPTIONS.get(args.project, ''),
                dry_run=args.dry_run,
            )
            results.append(r)
            time.sleep(1)
    finally:
        try:
            browser.close()
        except Exception:
            pass

    # 汇总
    sep = '=' * 60
    print(f"\n{sep}")
    print('📊 汇总')
    print(sep)

    statuses = {}
    for r in results:
        st = r['status']
        statuses[st] = statuses.get(st, 0) + 1

    for st, count in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f'  {st}: {count}')
    print(f'  总计: {len(results)}')

    if not args.dry_run:
        print()
        print('✅ 已完成，结果已写入 submissions 表和日志')
        for r in results:
            if r['success']:
                print(f'  ✅ ID {r["site_id"]}: {r["status"]}')
            else:
                print(f'  ❌ ID {r["site_id"]}: {r["status"]} — {r.get("reason", r.get("error", ""))[:60]}')


if __name__ == '__main__':
    main()
