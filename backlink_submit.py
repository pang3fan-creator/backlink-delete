#!/usr/bin/env python3
"""
外链提交脚本（agent-browser）
提交评论 + 自动记录到数据库和日志

用法：
python3 backlink_submit.py \
  --project "<项目名称>" \
  --submit-url "<要提交的外链URL>" \
  --site-id 123 \
  --url "<文章URL>" \
  --comment "<评论内容>"
"""

import argparse
import os
import re
import sqlite3
from datetime import datetime
from typing import Optional

from backlink_common import (
    DB_PATH,
    LOG_FILE,
    agent_browser_available,
    build_agent_browser_open_command,
    close_agent_browser,
    get_agent_browser_proxy,
    is_hard_worth_zero_reason,
    migrate_database,
    run_agent_browser,
)

DEFAULT_NAME = "Stefan M."
DEFAULT_EMAIL = "pang3fan@gmail.com"

# Bypass automation detection for sites that block headless browsers
os.environ.setdefault("AGENT_BROWSER_ARGS", "--disable-blink-features=AutomationControlled")

# WordPress 评论表单字段标签（支持中/英/法/葡/西/德/意）
NAME_LABELS = [
    "Name", "Name *", "Your Name", "姓名", "昵称",
    "Nom", "Nom *",
    "Nome", "Nome *", "Seu nome",
    "Nombre", "Nombre *", "Tu nombre",
    "Name *", "Ihr Name",
    "Nome", "Nome *", "Il tuo nome",
]
EMAIL_LABELS = [
    "Email", "Email *", "Your Email", "邮箱", "Email Address",
    "E-mail", "Adresse e-mail", "Courriel",
    "E-mail", "Seu e-mail",
    "Correo electrónico", "Correo",
    "E-Mail *", "Ihre E-Mail",
    "Email", "La tua email",
]
URL_LABELS = [
    "Website", "URL", "Your Website", "网站", "Website URL",
    "Site web", "Site Web",
    "Site", "Seu site",
    "Sitio web", "Web",
    "Website", "Ihre Website",
    "Sito web",
]
COMMENT_LABELS = [
    "Comment", "Your Comment", "评论", "Leave a Comment",
    "Commentaire", "Votre commentaire",
    "Comentário", "Seu comentário",
    "Comentario", "Tu comentario",
    "Kommentar", "Ihr Kommentar",
    "Commento", "Il tuo commento",
]
SUBMIT_TEXTS = [
    "Post Comment", "Submit", "Submit Comment", "发表评论", "提交",
    "Publier le commentaire", "Envoyer", "Soumettre",
    "Publicar comentário", "Enviar",
    "Publicar comentario", "Enviar",
    "Kommentar abschicken", "Abschicken", "Senden",
    "Pubblica il commento", "Invia",
]

# CSS 选择器回退（标准 WordPress 表单 + 通用 name 属性选择器）
CSS_FALLBACKS = [
    {"author": "#author", "email": "#email", "url": "#url", "comment": "#comment", "submit": "#submit"},
    {"author": "#comment-author", "email": "#comment-email", "url": "#comment-url", "comment": "#comment-comment", "submit": "#comment-submit"},
    {"author": "#comment_author", "email": "#comment_email", "url": "#comment_url", "comment": "#comment", "submit": "#comment-submit"},
    {"author": "input[name='author']", "email": "input[name='email']", "url": "input[name='url']", "comment": "textarea[name='comment']", "submit": "#submit, button[type='submit'], input[type='submit']"},
]

# 成功提示关键词（支持中/英/法/葡/西/德/意）
SUCCESS_INDICATORS = [
    '评论待审核',
    'Your comment is awaiting moderation',
    'Thank you for your comment',
    'Thanks for your comment',
    'Thank you for commenting',
    'awaiting moderation',
    '评论提交成功',
    '您的评论正在等待审核',
    'Votre commentaire attend modération',
    'Votre commentaire a été envoyé',
    'Merci pour votre commentaire',
    'Seu comentário aguarda moderação',
    'Obrigado pelo seu comentário',
    'Su comentario está pendiente de moderación',
    'Gracias por su comentario',
    'Ihr Kommentar wird geprüft',
    'Vielen Dank für Ihren Kommentar',
    'Il tuo commento è in attesa di moderazione',
    'Grazie per il tuo commento',
]


def log_to_file(site_url: str, project: str, submit_url: str, name: str, email: str,
                comment: str, result: str, comment_id: Optional[str] = None, target_url: str = ""):
    """追加一条提交记录到日志文件"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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


def save_to_db(
    site_id: str,
    project: str,
    status: str,
    notes: str = "",
    submit_url: str = "",
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
            submit_url, target_url, comment_text, comment_id, result_reason
        ) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(site_id, project_name) DO UPDATE SET
            status=?, notes=?, updated_at=?,
            submit_url=?, target_url=?, comment_text=?, comment_id=?, result_reason=?
    ''', (
        site_id, project, status, notes, now_ts, submit_url, target_url, comment_text, comment_id, result_reason,
        status, notes, now_ts, submit_url, target_url, comment_text, comment_id, result_reason
    ))
    conn.commit()
    conn.close()


def apply_site_worth_after_submission(site_id: str, success: bool, reason: str) -> None:
    migrate_database(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    try:
        if success:
            conn.execute(
                """
                UPDATE sites
                SET worth_submitting = 1,
                    skip_reason = NULL,
                    consecutive_failures = 0
                WHERE id = ?
                """,
                (site_id,),
            )
        elif is_hard_worth_zero_reason(reason):
            conn.execute(
                """
                UPDATE sites
                SET worth_submitting = 0,
                    skip_reason = ?,
                    consecutive_failures = COALESCE(consecutive_failures, 0) + 1
                WHERE id = ?
                """,
                (reason, site_id),
            )
        else:
            conn.execute(
                """
                UPDATE sites
                SET consecutive_failures = COALESCE(consecutive_failures, 0) + 1
                WHERE id = ?
                """,
                (site_id,),
            )
        conn.commit()
    finally:
        conn.close()


# ---- agent-browser 表单操作 ----

def _ab(cmd: list[str], timeout: int = 20) -> tuple[int, str, str]:
    """简化的 agent-browser 调用"""
    return run_agent_browser(["agent-browser"] + cmd, timeout=timeout)


def _try_fill_field(labels: list[str], text: str) -> bool:
    """尝试用语义标签定位并填写一个表单字段。返回是否成功。"""
    for label in labels:
        rc, _, _ = _ab(["find", "label", label, "fill", text], timeout=10)
        if rc == 0:
            return True
    return False


def _try_fill_field_placeholder(labels: list[str], text: str) -> bool:
    """用 placeholder 作为后备定位方式。"""
    for label in labels:
        rc, _, _ = _ab(["find", "placeholder", label, "fill", text], timeout=10)
        if rc == 0:
            return True
    return False


def _try_fill_field_css(css: str, text: str) -> bool:
    """用 CSS 选择器作为最后后备。"""
    rc, _, _ = _ab(["fill", css, text], timeout=10)
    return rc == 0


def _try_click_submit() -> bool:
    """尝试点击提交按钮。返回是否成功。"""
    for text in SUBMIT_TEXTS:
        rc, _, _ = _ab(["find", "text", text, "click"], timeout=10)
        if rc == 0:
            return True
    for text in SUBMIT_TEXTS:
        rc, _, _ = _ab(["find", "role", "button", "click", "--name", text], timeout=10)
        if rc == 0:
            return True
    return False


def fill_comment_form(name: str, email: str, submit_url: str, comment: str) -> bool:
    """
    三层回退填写 WordPress 评论表单：
    1. 语义 label 定位
    2. placeholder 定位
    3. CSS 选择器定位
    填写完毕后自动点击提交按钮。
    返回是否成功填写并提交。
    """
    # 第1层：语义 label
    ok_name = _try_fill_field(NAME_LABELS, name)
    ok_email = _try_fill_field(EMAIL_LABELS, email)
    ok_url = _try_fill_field(URL_LABELS, submit_url)
    ok_comment = _try_fill_field(COMMENT_LABELS, comment)
    if all([ok_name, ok_email, ok_url, ok_comment]):
        if _try_click_submit():
            return True

    # 第2层：placeholder
    ok_name = ok_name or _try_fill_field_placeholder(NAME_LABELS, name)
    ok_email = ok_email or _try_fill_field_placeholder(EMAIL_LABELS, email)
    ok_url = ok_url or _try_fill_field_placeholder(URL_LABELS, submit_url)
    ok_comment = ok_comment or _try_fill_field_placeholder(COMMENT_LABELS, comment)
    if all([ok_name, ok_email, ok_url, ok_comment]):
        if _try_click_submit():
            return True

    # 第3层：CSS 选择器
    for css_set in CSS_FALLBACKS:
        ok_name = ok_name or _try_fill_field_css(css_set["author"], name)
        ok_email = ok_email or _try_fill_field_css(css_set["email"], email)
        ok_url = ok_url or _try_fill_field_css(css_set["url"], submit_url)
        ok_comment = ok_comment or _try_fill_field_css(css_set["comment"], comment)
        if all([ok_name, ok_email, ok_url, ok_comment]):
            rc, _, _ = _ab(["click", css_set["submit"]], timeout=10)
            if rc == 0:
                return True

    return False


def detect_submission_result() -> dict:
    """
    检测提交是否成功。
    返回 {'found': bool, 'comment_id': str|None, 'reason': str}
    """
    import time

    # 1. 等待页面变化
    _ab(["wait", "--load", "networkidle"], timeout=25)
    time.sleep(1)

    # 2. 检查 URL 中的 #comment- 锚点
    rc, url, _ = _ab(["get", "url"], timeout=5)
    if '#comment-' in url:
        cid = url.split('#comment-')[-1].split('&')[0].split('#')[0]
        return {'found': True, 'comment_id': cid, 'reason': 'url_comment'}

    # 3. 等待成功提示文字
    for indicator in SUCCESS_INDICATORS:
        rc, _, _ = _ab(["wait", "--text", indicator], timeout=8)
        if rc == 0:
            return {'found': True, 'comment_id': _extract_comment_id(), 'reason': f'success_text: {indicator}'}

    # 4. 检查页面快照中的成功提示
    rc, snapshot, _ = _ab(["snapshot", "-i"], timeout=5)
    snapshot_lower = snapshot.lower()
    for indicator in SUCCESS_INDICATORS:
        if indicator.lower() in snapshot_lower:
            return {'found': True, 'comment_id': _extract_comment_id(), 'reason': f'snapshot_text: {indicator}'}

    # 5. 检查 awaiting-moderation 类名
    rc, _, _ = _ab(["wait", ".comment-awaiting-moderation, .comment-pending, .awaiting-moderation"], timeout=5)
    if rc == 0:
        return {'found': True, 'comment_id': None, 'reason': 'awaiting_moderation_element'}

    return {'found': False, 'comment_id': None, 'reason': 'no_success_indicator'}


def _extract_comment_id() -> Optional[str]:
    """从当前页面 URL 或文本中提取评论 ID"""
    import re
    rc, url, _ = _ab(["get", "url"], timeout=5)
    m = re.search(r'#comment[_-](\d+)', url)
    if m:
        return m.group(1)
    rc, text, _ = _ab(["get", "text", "body"], timeout=5)
    for pattern in [r'comment[_-]id[_:]\s*(\d+)', r'comment-(\d+)']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def submit_comment(project: str, submit_url: str, site_id: str, article_url: str,
                   comment: str, name: str = DEFAULT_NAME, email: str = DEFAULT_EMAIL) -> dict:
    """
    使用 agent-browser 提交评论

    参数:
        project:     项目名称（直接用作 DB 的 project_name）
        submit_url:  要提交的外链 URL
        site_id:     站点 ID
        article_url: 目标文章 URL
        comment:     评论内容

    返回: {
        'success': bool,
        'status': str,
        'comment_id': str or None,
        'error': str or None,
        'form_found': bool,
        'form_submitted': bool,
    }
    """
    if not agent_browser_available():
        return {
            'success': False, 'status': '失败', 'comment_id': None,
            'error': 'agent-browser 未安装。请运行: npm i -g agent-browser && agent-browser install',
            'form_found': None, 'form_submitted': None
        }

    proxy = get_agent_browser_proxy()

    def _fail(status: str, error: str, form_found=None, form_submitted=None) -> dict:
        return {
            'success': False, 'status': status, 'comment_id': None,
            'error': error, 'form_found': form_found, 'form_submitted': form_submitted
        }

    try:
        # 启动浏览器并打开页面
        open_cmd = build_agent_browser_open_command(article_url, proxy=proxy)
        rc, _, err = _ab_open(open_cmd, timeout=60)
        # 有些站点 agent-browser open 会超时但页面实际已加载
        # 先检查浏览器是否已到了目标页面
        _, current_url, _ = _ab(["get", "url"], timeout=5)
        if rc != 0 and not current_url:
            close_agent_browser(True)
            return _fail('已失效' if 'timeout' in err.lower() else '失败', f'页面无法打开: {err.strip() or "unknown error"}')

        # 等待页面加载（如果上面已经超时，这里可能会报错，忽略）
        _ab(["wait", "--load", "networkidle"], timeout=30)

        # 检测登录
        rc, url, _ = _ab(["get", "url"], timeout=5)
        if 'wp-login.php' in url or '/login' in url.lower():
            close_agent_browser()
            return _fail('需登录', '页面重定向到登录页', form_found=False, form_submitted=False)

        # 填写并提交表单
        form_filled = fill_comment_form(name, email, submit_url, comment)

        if not form_filled:
            close_agent_browser()
            return _fail('失败', '找不到评论表单', form_found=False, form_submitted=False)

        # 检测提交结果
        result = detect_submission_result()
        close_agent_browser()

        if result['found']:
            return {
                'success': True, 'status': '已提交', 'comment_id': result['comment_id'],
                'error': None, 'form_found': True, 'form_submitted': True,
                'result_reason': result['reason']
            }
        else:
            return {
                'success': False, 'status': '待确认', 'comment_id': None,
                'error': f'表单已提交但未检测到确认（{result["reason"]}）',
                'form_found': True, 'form_submitted': True,
                'result_reason': result['reason']
            }

    except Exception as e:
        close_agent_browser(True)
        return _fail('失败', str(e))


def _ab_open(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """打开页面的专用调用（超时更长）"""
    return run_agent_browser(cmd, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description="外链提交脚本（agent-browser）")
    parser.add_argument("--project", required=True, help="项目名称（用作 DB 记录的项目标识）")
    parser.add_argument("--submit-url", required=True, help="要提交的外链 URL")
    parser.add_argument("--site-id", required=True, help="站点 ID")
    parser.add_argument("--url", required=True, help="目标文章 URL")
    parser.add_argument("--comment", required=True, help="评论内容")
    parser.add_argument("--name", default=DEFAULT_NAME, help="姓名")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="邮箱")
    
    args = parser.parse_args()
    migrate_database(DB_PATH)
    
    print(f"🐍 开始提交")
    print(f"   站点ID: {args.site_id}")
    print(f"   项目: {args.project}")
    print(f"   文章: {args.url}")
    print(f"   外链: {args.submit_url}")
    print()
    
    result = submit_comment(
        project=args.project,
        submit_url=args.submit_url,
        site_id=args.site_id,
        article_url=args.url,
        comment=args.comment,
        name=args.name,
        email=args.email
    )
    
    log_to_file(
        site_url=args.url,
        project=args.project,
        submit_url=args.submit_url,
        name=args.name,
        email=args.email,
        comment=args.comment,
        result=result['status'] if result['success'] else f"{result['status']}: {result['error']}",
        comment_id=result.get('comment_id'),
        target_url=args.url
    )
    
    save_to_db(
        site_id=args.site_id,
        project=args.project,
        status=result['status'],
        notes=result.get('error') or "",
        submit_url=args.submit_url,
        target_url=args.url,
        comment_text=args.comment,
        comment_id=result.get('comment_id'),
        result_reason=result.get('result_reason') or result.get('error') or ""
    )

    apply_site_worth_after_submission(
        args.site_id,
        result["success"],
        result.get("result_reason") or result.get("error") or "",
    )
    
    if result['success']:
        print(f"✅ 提交成功！评论ID: {result['comment_id']}")
    else:
        print(f"❌ 提交失败: {result['error']}")
        if result.get('form_found') and result.get('form_submitted'):
            print(f"💡 表单已提交，但无法确认结果。建议手动检查页面。")
    
    print(f"📝 已记录到数据库和日志")


if __name__ == "__main__":
    main()
