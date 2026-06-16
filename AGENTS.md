# Backlink 提交 SOP

## 标准信息

**邮箱**：pang3fan@gmail.com

**三个项目**：
| 项目 | 域名 |
|------|------|
| extractkeywords | extractkeywords.com |
| tryschedule | tryschedule.com |
| heicpdf | heicpdf.to |

---

## 核心原则

1. **留下链接是底线** — 没链接 = 白干
2. **Website 字段必填** — 这是外链的唯一来源
3. **评论正文不带网址** — 更自然，通过率更高
4. **先评估再提交** — 不值得的标记 worth=0 后跳过
5. **失败原因结构化** — `submissions.notes/result_reason` 和 `sites.skip_reason` 必须写清楚

---

## 状态定义

`submissions.status` 统一只使用以下值：

| 状态 | 含义 |
|------|------|
| 已提交 | 已确认提交成功或进入审核 |
| 待确认 | 表单已提交，但页面没有明确成功信号 |
| 失败 | 本次尝试失败，notes/result_reason 说明原因 |
| 需付费 | 站点需要付费才能提交 |
| 需登录 | 站点需要登录或 OAuth |
| 需验证码 | 站点有验证码，需人工处理 |
| 已失效 | 页面不可访问、404、证书错误、长期超时 |
| 跳过 | 不适合提交，原因写入 notes/result_reason |

`sites.worth_submitting` 规则：

| 值 | 含义 | 必填说明 |
|----|------|----------|
| NULL | 未评估 | 下次继续评估 |
| 1 | 值得提交 | 有评论表单且有 Website/URL 字段 |
| 0 | 不值得提交 | 必须写 `sites.skip_reason` |

---

## 提交流程（blog_comment）

**每次接任务，按以下步骤执行：**

1. **从数据库取待处理站点**
   ```bash
   python3 -c "
   import sqlite3
   db = sqlite3.connect('backlinks.db')
   cur = db.cursor()
   cur.execute('''
     SELECT s.id, s.site_url, s.worth_submitting
     FROM sites s
     LEFT JOIN submissions sb ON s.id = sb.site_id AND sb.project_name = 'extractkeywords.com'
     WHERE s.site_type = 'blog_comment' AND sb.id IS NULL
     LIMIT 5
   ''')
   for r in cur.fetchall():
       print(f'{r[0]}: {r[1]} (worth={r[2]})')
   "
   ```

2. **评估 worth_submitting（如果为 NULL）**
   - 用 CloakBrowser 打开页面
   - 有评论表单且有 URL 字段 → worth=1
   - 无评论 / Jetpack iframe / 评论区关闭 / 无 Website 字段 → worth=0，并写 `skip_reason`
   ```bash
   python3 -c "
   import sqlite3
   db = sqlite3.connect('backlinks.db')
   db.execute('UPDATE sites SET worth_submitting = 1, skip_reason = NULL WHERE id = <site_id>')
   db.commit()
   "
   ```

3. **提交评论（worth=1 的站点）**
   ```bash
   python3 backlink_submit.py \
     --project extractkeywords \
     --site-id <site_id> \
     --url "<文章URL>" \
     --comment "<评论内容>"
   ```

4. **手动兜底（脚本失败时）**
   - 用 CloakBrowser 手动打开、填表、提交
   - 记录结果：
   ```bash
   python3 backlink_db.py add-submission <site_id> extractkeywords.com 已提交 \
     --url "<文章URL>" \
     --comment "<评论内容>" \
     --comment-id "<评论ID>" \
     --reason "手动提交成功"
   ```

---

## 常用命令

```bash
# 查看统计
python3 backlink_db.py stats

# 标记 worth=0（不值得）
python3 -c "
import sqlite3
db = sqlite3.connect('backlinks.db')
db.execute('UPDATE sites SET worth_submitting = 0, skip_reason = \"无 Website 字段\" WHERE id = <site_id>')
db.commit()
"

# 标记 worth=1（值得）
python3 -c "
import sqlite3
db = sqlite3.connect('backlinks.db')
db.execute('UPDATE sites SET worth_submitting = 1, skip_reason = NULL WHERE id = <site_id>')
db.commit()
"
```

---

## 注意事项

- **浏览器**：全程用 CloakBrowser，禁止 Hermes 内置浏览器
- **项目参数**：`--project` 用短名（extractkeywords / tryschedule / heicpdf）
- **失败记录**：必须写 notes，说明具体原因
- **提交证据**：博客评论要记录 `target_url/comment_text/comment_id/result_reason`
- **一站点三项目**：错开时间提交，不要同时提交三个

---

**版本**: v6.1 | **更新**: 2026-06-16
