# Backlink 提交 SOP

## 一、标准信息

**邮箱**：pang3fan@gmail.com

**三个项目**：
| 项目 | 域名 | 数据库名称 |
|------|------|-----------|
| extractkeywords | extractkeywords.com | extractkeywords.com |
| tryschedule | tryschedule.com | tryschedule.com |
| heicpdf | heicpdf.to | heicpdf.to |

---

## 二、核心原则（最重要！）

1. **留下链接是底线！** 没有链接 = 白干
2. **Website 字段必须填！** 这就是外链
3. **评论尽量优雅** — 结合文章内容生成，不是垃圾评论
4. 外链本质是宣传，删不删是站长的事，先提交再说

---

## 三、提交流程

### 浏览器优先级
1. **第一优先**：CloakBrowser（`from cloakbrowser import launch`）
2. **备选**：实在没办法时，才用 Hermes 内置浏览器

### CloakBrowser 代码模板

```python
from cloakbrowser import launch

browser = launch(headless=True, proxy="http://127.0.0.1:7890")
context = browser.new_context()
page = context.new_page()

page.goto("文章URL", timeout=30000)

# 填写表单（Website 字段必须填！）
page.query_selector('#author').fill('Stefan M.')
page.query_selector('#email').fill('pang3fan@gmail.com')
page.query_selector('#url').fill('https://extractkeywords.com')  # 链接！
page.query_selector('#comment').fill('评论内容')

page.query_selector('#submit').click()
page.wait_for_timeout(2000)

# 检查成功：URL 包含 #comment-
browser.close()
```

---

## 四、记录命令

```bash
# 提交后记录
python3 bl.py add-submission <site_id> extractkeywords.com 已提交 \
  --url "https://extractkeywords.com" \
  --comment "评论内容" \
  --comment-id "12345"

# 查看统计
python3 bl.py stats
```

**状态定义**：
- `已提交` — 表单递交成功
- `失败` — 提交失败
- `需付费` — 需付费
- `需登录` — 需注册

---

## 五、障碍处理

| 障碍 | 处理 |
|------|------|
| 验证码 | 填好表单，等主人过验证码 |
| 需登录 | 跳过，标记到数据库 |
| 404/失效 | 跳过，标记到数据库 |
| 需付费 | 记录费用，主人决定 |

---

## 六、注意事项

1. **禁止主动导出 Excel** — 只有主人说"导出"时才执行
2. **一站点三项目** — 错开时间提交，不要同时提交三个

---

**文档版本**: v3.0
**最后更新**: 2026-06-12
