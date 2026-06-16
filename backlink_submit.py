#!/usr/bin/env python3
"""
外链提交脚本（CloakBrowser）
提交评论 + 自动记录到数据库和日志

用法：
python3 backlink_submit.py --project extractkeywords --site-id 123 --url "https://example.com/blog/post" --comment "评论内容"
"""

import argparse
import sqlite3
import re
import sys
from datetime import datetime
from typing import Optional

from backlink_common import DB_PATH, LOG_FILE, VALID_STATUSES, migrate_database

PROJECT_URLS = {
    "extractkeywords": "https://extractkeywords.com",
    "tryschedule": "https://tryschedule.com",
    "heicpdf": "https://heicpdf.to"
}

# 项目 short name → 数据库用的完整项目名
PROJECT_DB_NAMES = {
    "extractkeywords": "extractkeywords.com",
    "tryschedule": "tryschedule.com",
    "heicpdf": "heicpdf.to"
}

# 标准信息
DEFAULT_NAME = "Stefan M."
DEFAULT_EMAIL = "pang3fan@gmail.com"

# WordPress 评论表单选择器组合
FORM_SELECTORS = [
    # 标准 WordPress
    {'author': '#author', 'email': '#email', 'url': '#url', 'comment': '#comment', 'submit': '#submit'},
    # 备选命名
    {'author': '#comment-author', 'email': '#comment-email', 'url': '#comment-url', 'comment': '#comment-comment', 'submit': '#comment-submit'},
    # 再备选
    {'author': '#comment_author', 'email': '#comment_email', 'url': '#comment_url', 'comment': '#comment', 'submit': '#comment-submit'},
]

# 成功提示关键词（检测提交结果）
SUCCESS_INDICATORS = [
    '评论待审核',
    'Your comment is awaiting moderation',
    'Thank you for your comment',
    'Thanks for your comment',
    'Thank you for commenting',
    'awaiting moderation',
    '评论提交成功',
    '您的评论正在等待审核',
]


def log_to_file(site_url: str, project: str, submit_url: str, name: str, email: str,
                comment: str, result: str, comment_id: Optional[str] = None):
    """追加一条提交记录到日志文件"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    entry = f"""=== {timestamp} ===
站点：{site_url}
项目：{project}
姓名：{name}
邮箱：{email}
网址：{submit_url}
评论：{comment}
结果：{result}"""
    
    if comment_id:
        entry += f"，评论ID: {comment_id}"
    
    entry += "\n\n"
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def save_to_db(
    site_id: str,
    project: str,
    status: str,
    notes: str = "",
    target_url: str = "",
    comment_text: str = "",
    comment_id: Optional[str] = None,
    result_reason: str = "",
):
    """保存提交记录到数据库"""
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO submissions (
            site_id, project_name, status, notes, updated_at,
            target_url, comment_text, comment_id, result_reason
        ) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(site_id, project_name) DO UPDATE SET
            status=?,
            notes=?,
            updated_at=?,
            target_url=?,
            comment_text=?,
            comment_id=?,
            result_reason=?
    ''', (
        site_id, project, status, notes, now_ts, target_url, comment_text, comment_id, result_reason,
        status, notes, now_ts, target_url, comment_text, comment_id, result_reason
    ))
    
    conn.commit()
    conn.close()


def try_fill_form(page, name: str, email: str, submit_url: str, comment: str) -> Optional[str]:
    """
    尝试用多种选择器组合填写评论表单。
    返回 'ok' 或错误描述。
    """
    for selectors in FORM_SELECTORS:
        try:
            author_el = page.query_selector(selectors['author'])
            email_el = page.query_selector(selectors['email'])
            url_el = page.query_selector(selectors['url'])
            comment_el = page.query_selector(selectors['comment'])
            submit_el = page.query_selector(selectors['submit'])
            
            if all([author_el, email_el, url_el, comment_el, submit_el]):
                author_el.fill(name)
                email_el.fill(email)
                url_el.fill(submit_url)
                comment_el.fill(comment)
                submit_el.click()
                return 'ok'
        except Exception:
            continue
    
    return None


def check_success(page) -> dict:
    """
    检查提交是否成功。
    返回 {'found': bool, 'comment_id': str|None, 'reason': str}
    """
    # 1. 检查 URL 中的 #comment-
    current_url = page.url
    if '#comment-' in current_url:
        cid = current_url.split('#comment-')[-1].split('&')[0].split('#')[0]
        return {'found': True, 'comment_id': cid, 'reason': 'url_comment'}
    
    # 2. 等待页面刷新/重载
    import time
    time.sleep(2)
    current_url = page.url
    if '#comment-' in current_url:
        cid = current_url.split('#comment-')[-1].split('&')[0].split('#')[0]
        return {'found': True, 'comment_id': cid, 'reason': 'url_comment_delayed'}
    
    # 3. 检查页面内容中的成功提示
    page_text = page.inner_text('body') if page.query_selector('body') else ''
    for indicator in SUCCESS_INDICATORS:
        if indicator.lower() in page_text.lower():
            # 尝试提取评论ID
            cid = extract_comment_id(page, page_text)
            return {'found': True, 'comment_id': cid, 'reason': f'success_text: {indicator}'}
    
    # 4. 检查是否有 pending/awaiting 类
    pending = page.query_selector('.comment-awaiting-moderation, .comment-pending, .awaiting-moderation')
    if pending:
        return {'found': True, 'comment_id': None, 'reason': 'awaiting_moderation_element'}
    
    return {'found': False, 'comment_id': None, 'reason': 'no_success_indicator'}


def extract_comment_id(page, page_text: str) -> Optional[str]:
    """尝试从页面内容或 URL 提取评论ID"""
    # 从 URL
    m = re.search(r'#comment[_-](\d+)', page.url)
    if m:
        return m.group(1)
    
    # 从页面文本
    for pattern in [
        r'comment[_-]id[_:]\s*(\d+)',
        r'评论[_-]?ID[：:]\s*(\d+)',
        r'comment-(\d+)',
    ]:
        m = re.search(pattern, page_text, re.IGNORECASE)
        if m:
            return m.group(1)
    
    return None


def submit_comment(project: str, site_id: str, article_url: str, comment: str,
                   name: str = DEFAULT_NAME, email: str = DEFAULT_EMAIL) -> dict:
    """
    使用 CloakBrowser 提交评论
    
    返回: {
        'success': bool,
        'status': str,
        'comment_id': str or None,
        'error': str or None,
        'form_found': bool,   # 是否找到了表单
        'form_submitted': bool,  # 是否成功提交了表单
    }
    """
    try:
        from cloakbrowser import launch
    except ModuleNotFoundError:
        return {'success': False, 'status': '失败', 'comment_id': None,
                'error': '缺少 cloakbrowser 依赖，无法自动提交。请安装依赖或按 SOP 手动兜底。',
                'form_found': None, 'form_submitted': None}
    
    submit_url = PROJECT_URLS.get(project, f"https://{project}.com")
    
    try:
        browser = launch(headless=True, proxy="http://127.0.0.1:7890")
        context = browser.new_context()
        page = context.new_page()
        
        # 打开文章页面
        page.goto(article_url, timeout=30000)
        
        # 检查是否需登录
        if page.query_selector('.logged-in') or 'wp-login.php' in page.url or 'login' in page.url.lower():
            browser.close()
            return {'success': False, 'status': '需登录', 'comment_id': None, 'error': '需要登录',
                    'form_found': False, 'form_submitted': False}
        
        # 尝试填写表单（多种选择器）
        form_result = try_fill_form(page, name, email, submit_url, comment)
        
        if form_result != 'ok':
            # 找不到表单
            browser.close()
            return {'success': False, 'status': '失败', 'comment_id': None, 'error': '找不到评论表单',
                    'form_found': False, 'form_submitted': False}
        
        # 表单已提交，检查结果
        result = check_success(page)
        browser.close()
        
        if result['found']:
            return {'success': True, 'status': '已提交', 'comment_id': result['comment_id'], 'error': None,
                    'form_found': True, 'form_submitted': True, 'result_reason': result['reason']}
        else:
            return {'success': False, 'status': '待确认', 'comment_id': None, 
                    'error': f'提交成功但未检测到确认（{result["reason"]}）',
                    'form_found': True, 'form_submitted': True, 'result_reason': result['reason']}
            
    except Exception as e:
        return {'success': False, 'status': '失败', 'comment_id': None, 'error': str(e),
                'form_found': None, 'form_submitted': None}


def main():
    parser = argparse.ArgumentParser(description="外链提交脚本（CloakBrowser）")
    parser.add_argument("--project", required=True, 
                        choices=["extractkeywords", "tryschedule", "heicpdf"],
                        help="项目名称")
    parser.add_argument("--site-id", required=True, help="站点 ID")
    parser.add_argument("--url", required=True, help="文章 URL")
    parser.add_argument("--comment", required=True, help="评论内容")
    parser.add_argument("--name", default=DEFAULT_NAME, help="姓名")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="邮箱")
    
    args = parser.parse_args()
    migrate_database(DB_PATH)
    
    submit_url = PROJECT_URLS[args.project]
    db_project = PROJECT_DB_NAMES[args.project]
    
    print(f"🐍 开始提交")
    print(f"   站点ID: {args.site_id}")
    print(f"   项目: {db_project}")
    print(f"   文章: {args.url}")
    print(f"   网址: {submit_url}")
    print()
    
    # 提交评论
    result = submit_comment(
        project=args.project,
        site_id=args.site_id,
        article_url=args.url,
        comment=args.comment,
        name=args.name,
        email=args.email
    )
    
    # 记录到日志
    log_to_file(
        site_url=args.url,
        project=db_project,
        submit_url=submit_url,
        name=args.name,
        email=args.email,
        comment=args.comment,
        result=result['status'] if result['success'] else f"{result['status']}: {result['error']}",
        comment_id=result.get('comment_id')
    )
    
    # 记录到数据库
    save_to_db(
        site_id=args.site_id,
        project=db_project,
        status=result['status'],
        notes=result.get('error') or "",
        target_url=args.url,
        comment_text=args.comment,
        comment_id=result.get('comment_id'),
        result_reason=result.get('result_reason') or result.get('error') or ""
    )
    
    # 输出结果
    if result['success']:
        print(f"✅ 提交成功！评论ID: {result['comment_id']}")
    else:
        print(f"❌ 提交失败: {result['error']}")
        
        # 如果找到了表单但检测失败（可能成功但没识别到），提示手动检查
        if result.get('form_found') and result.get('form_submitted'):
            print(f"💡 表单已提交，但无法确认结果。建议手动检查页面。")
    
    print(f"📝 已记录到数据库和日志")


if __name__ == "__main__":
    main()
