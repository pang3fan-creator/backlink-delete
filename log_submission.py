#!/usr/bin/env python3
"""
日志记录脚本 - 记录博客评论提交过程
用法：python3 log_submission.py --site <站点URL> --project <项目名> --url <提交的网址> --comment <评论内容> --result <结果>
"""

import argparse
from datetime import datetime
from pathlib import Path

# 项目配置
PROJECT_URLS = {
    "extractkeywords": "https://extractkeywords.com",
    "tryschedule": "https://tryschedule.com",
    "heicpdf": "https://heicpdf.to"
}

# 日志文件路径
LOG_FILE = Path(__file__).parent / "logs" / "submission.log"


def log_submission(site: str, project: str, url: str, name: str, email: str, 
                   comment: str, result: str, comment_id: str = None):
    """追加一条提交记录到日志文件"""
    
    # 确保 logs 目录存在
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建日志条目
    entry = f"""=== {timestamp} ===
站点：{site}
项目：{project}
姓名：{name}
邮箱：{email}
网址：{url}
评论：{comment}
结果：{result}"""
    
    if comment_id:
        entry += f"，评论ID: {comment_id}"
    
    entry += "\n\n"
    
    # 追加到日志文件
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
    
    print(f"✅ 日志已记录到 {LOG_FILE}")


def main():
    parser = argparse.ArgumentParser(description="记录博客评论提交过程")
    parser.add_argument("--site", required=True, help="目标站点URL")
    parser.add_argument("--project", required=True, 
                        choices=["extractkeywords", "tryschedule", "heicpdf"],
                        help="项目名称")
    parser.add_argument("--url", required=True, help="提交的网址")
    parser.add_argument("--name", default="Stefan M.", help="填写的姓名")
    parser.add_argument("--email", default="pang3fan@gmail.com", help="填写的邮箱")
    parser.add_argument("--comment", required=True, help="评论内容")
    parser.add_argument("--result", required=True, 
                        choices=["成功", "失败", "待审核"],
                        help="提交结果")
    parser.add_argument("--comment-id", help="评论ID（如果成功）")
    
    args = parser.parse_args()
    
    log_submission(
        site=args.site,
        project=args.project,
        url=args.url,
        name=args.name,
        email=args.email,
        comment=args.comment,
        result=args.result,
        comment_id=args.comment_id
    )


if __name__ == "__main__":
    main()
