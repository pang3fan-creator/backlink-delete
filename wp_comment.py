#!/usr/bin/env python3
"""
WordPress 博客评论提交脚本
生成可直接在浏览器控制台执行的 JS 代码

用法：
python3 wp_comment.py --project tryschedule --comment "评论内容"
"""

import argparse

# 项目配置
PROJECT_URLS = {
    "extractkeywords": "https://extractkeywords.com",
    "tryschedule": "https://tryschedule.com",
    "heicpdf": "https://heicpdf.to"
}

def generate_js(project: str, comment: str, name: str = "Stefan M.", email: str = "pang3fan@gmail.com") -> str:
    """生成 WordPress 评论提交的 JS 代码"""
    url = PROJECT_URLS.get(project, f"https://{project}.com")
    
    js = f"""// === WordPress 博客评论一键提交 ===
document.getElementById('author').value = '{name}';
document.getElementById('email').value = '{email}';
document.getElementById('url').value = '{url}';
document.getElementById('comment').value = `{comment}`;
document.getElementById('submit').click();"""
    
    return js


def main():
    parser = argparse.ArgumentParser(description="生成 WordPress 评论提交 JS")
    parser.add_argument("--project", required=True, 
                        choices=["extractkeywords", "tryschedule", "heicpdf"],
                        help="项目名称")
    parser.add_argument("--comment", required=True, help="评论内容")
    parser.add_argument("--name", default="Stefan M.", help="填写的姓名")
    parser.add_argument("--email", default="pang3fan@gmail.com", help="填写的邮箱")
    
    args = parser.parse_args()
    
    js = generate_js(args.project, args.comment, args.name, args.email)
    print(js)
    print(f"\n// 提交的网址: {PROJECT_URLS[args.project]}")


if __name__ == "__main__":
    main()
