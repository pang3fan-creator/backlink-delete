#!/usr/bin/env python3
"""
外链提交脚本（CloakBrowser）
提交评论 + 自动记录到数据库和日志

用法：
python3 backlink_submit.py --project extractkeywords --site-id 123 --url "https://example.com/blog/post" --comment "评论内容"
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# 项目配置
PROJECT_URLS = {
    "extractkeywords": "https://extractkeywords.com",
    "tryschedule": "https://tryschedule.com",
    "heicpdf": "https://heicpdf.to"
}

# 标准信息
DEFAULT_NAME = "Stefan M."
DEFAULT_EMAIL = "pang3fan@gmail.com"

# 路径
DB_PATH = Path(__file__).parent / "backlinks.db"
LOG_FILE = Path(__file__).parent / "logs" / "submission.log"

# 允许的状态
VALID_STATUSES = ['已提交', '失败', '需付费', '需登录']


def log_to_file(site_url: str, project: str, submit_url: str, name: str, email: str,
                comment: str, result: str, comment_id: str | None = None):
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


def save_to_db(site_id: str, project: str, status: str, notes: str = ""):
    """保存提交记录到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    
    now_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO submissions (site_id, project_name, status, notes, updated_at) 
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(site_id, project_name) DO UPDATE SET status=?, notes=?, updated_at=?
    ''', (site_id, project, status, notes, now_ts, status, notes, now_ts))
    
    conn.commit()
    conn.close()


def submit_comment(project: str, site_id: str, article_url: str, comment: str,
                   name: str = DEFAULT_NAME, email: str = DEFAULT_EMAIL) -> dict:
    """
    使用 CloakBrowser 提交评论
    
    返回: {
        'success': bool,
        'status': str,  # 已提交/失败/需付费/需登录
        'comment_id': str or None,
        'error': str or None
    }
    """
    from cloakbrowser import launch
    
    submit_url = PROJECT_URLS.get(project, f"https://{project}.com")
    
    try:
        browser = launch(headless=True, proxy="http://127.0.0.1:7890")
        context = browser.new_context()
        page = context.new_page()
        
        # 打开文章页面
        page.goto(article_url, timeout=30000)
        
        # 填写表单
        author_field = page.query_selector('#author')
        email_field = page.query_selector('#email')
        url_field = page.query_selector('#url')
        comment_field = page.query_selector('#comment')
        submit_btn = page.query_selector('#submit')
        
        if not all([author_field, email_field, url_field, comment_field, submit_btn]):
            # 检查是否需要登录
            if page.query_selector('.logged-in') or 'wp-login.php' in page.url:
                return {'success': False, 'status': '需登录', 'comment_id': None, 'error': '需要登录'}
            return {'success': False, 'status': '失败', 'comment_id': None, 'error': '找不到评论表单'}
        
        author_field.fill(name)
        email_field.fill(email)
        url_field.fill(submit_url)
        comment_field.fill(comment)
        
        # 提交
        submit_btn.click()
        page.wait_for_timeout(3000)
        
        # 检查结果：URL 包含 #comment- 表示成功
        final_url = page.url
        browser.close()
        
        if '#comment-' in final_url:
            comment_id = final_url.split('#comment-')[-1].split('&')[0].split('#')[0]
            return {'success': True, 'status': '已提交', 'comment_id': comment_id, 'error': None}
        else:
            return {'success': False, 'status': '失败', 'comment_id': None, 'error': '提交后未跳转到评论'}
            
    except Exception as e:
        return {'success': False, 'status': '失败', 'comment_id': None, 'error': str(e)}


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
    
    submit_url = PROJECT_URLS[args.project]
    
    print(f"🐍 开始提交")
    print(f"   站点ID: {args.site_id}")
    print(f"   项目: {args.project}")
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
        project=args.project,
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
        project=args.project,
        status=result['status'],
        notes=result.get('error') or ""
    )
    
    # 输出结果
    if result['success']:
        print(f"✅ 提交成功！评论ID: {result['comment_id']}")
    else:
        print(f"❌ 提交失败: {result['error']}")
    
    print(f"📝 已记录到数据库和日志")


if __name__ == "__main__":
    main()
