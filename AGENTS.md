# Backlink 提交 SOP

## 标准信息

**邮箱**：pang3fan@gmail.com

**项目**：每次提交时由主人指定 `--project` 和 `--submit-url`，不预设固定项目列表。

---

## 核心原则

1. **留下链接是底线** — 没链接 = 白干
2. **Website 字段必填** — 这是外链的唯一来源
3. **评论正文不带网址** — 更自然，通过率更高
4. **先评估再提交** — 不值得的标记 worth=0 后跳过
5. **失败原因结构化** — `submissions.notes/result_reason` 和 `sites.skip_reason` 必须写清楚
6. **worth=0 从严** — 只标记站点级硬障碍，不用来表示一次预检或自动化失败
7. **不再使用 Excel** — `backlinks.xlsx` 已废弃；`backlink_db.py` 仅保留 SQLite 辅助命令
8. **迁移会补视图** — `migrate_database()` 会补 `consecutive_failures` 并生成 `view_<project>` 只读视图

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
| 1 | 值得继续尝试 | 自动可提交、人工可能可处理、历史成功过都归这里 |
| 0 | 硬性不值得 | 必须写 `sites.skip_reason`，仅限 404/DNS/SSL/长期超时/明确无 Website 字段等硬障碍 |

详细判定见 `0-Develop_Doc/WORTH_SUBMITTING_LOGIC.md`。

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
     LEFT JOIN submissions sb ON s.id = sb.site_id AND sb.project_name = '<project_name>'
     WHERE s.site_type = 'blog_comment'
       AND sb.id IS NULL
       AND COALESCE(s.worth_submitting, 1) != 0
     LIMIT 5
   ''')
   for r in cur.fetchall():
       print(f'{r[0]}: {r[1]} (worth={r[2]})')
   "
   ```

2. **评估 worth_submitting（如果为 NULL）**
   - 用 agent-browser 打开页面
   ```bash
   kill -9 $(ps aux | grep -v grep | grep -E "agent-browser|Chrome" | awk '{print $2}') 2>/dev/null; sleep 2
   ```
   - **DOM 级检查**（用 `eval` 验证，不能只看页面文字）：
     ```
     // 检查是否有评论表单
     document.querySelector('#commentform, .comment-form, #respond form')
     // 检查是否有 Website 字段
     document.querySelector('input[name="url"], input[name="website"]')
     ```
   - 有评论表单 **且** 有 URL/Website 字段 → worth=1
   - 页面不可访问 / 404 / SSL / 长期超时 → worth=0，并写 `skip_reason`
   - 明确无 Website 字段 / 明确拒绝外部链接等硬障碍 → worth=0，并写 `skip_reason`
   - 登录墙 / 验证码 / Cloudflare / 自动化没找到表单 / 表单复杂 → 优先保留为 worth=1；如果信息还不足，再保留 NULL
   ```bash
   python3 -c "
   import sqlite3
   db = sqlite3.connect('backlinks.db')
   db.execute('UPDATE sites SET worth_submitting = 1, skip_reason = NULL WHERE id = <site_id>')
   db.commit()
   "
   ```
   硬障碍标记 worth=0：
   ```bash
   python3 -c "
   import sqlite3
   db = sqlite3.connect('backlinks.db')
   db.execute('UPDATE sites SET worth_submitting = 0, skip_reason = \"<硬障碍原因>\" WHERE id = <site_id>')
   db.commit()
   "
   ```

3. **预检 worth=1 站点（提交前必做）**
   ```bash
   kill -9 $(ps aux | grep -v grep | grep -E "agent-browser|Chrome" | awk '{print $2}') 2>/dev/null; sleep 2
   python3 prevalidate.py --project "<project_name>" --apply
   ```
   - 对每个 worth=1 未提交站点，自动检查：页面可达 → 有评论表单 → 有 Website 字段
   - `--apply` 只把硬障碍标记为 worth=0 + skip_reason；普通预检失败保留 worth，不降级
   - 通过预检的站点才进入提交阶段，避免打开文章写评论后发现没表单

4. **提交评论（通过预检的站点）**
   ```bash
   kill -9 $(ps aux | grep -v grep | grep -E "agent-browser|Chrome" | awk '{print $2}') 2>/dev/null; sleep 2
   python3 backlink_submit.py \
     --project "<project_name>" \
     --submit-url "<你要提交的外链URL>" \
     --site-id <site_id> \
     --url "<文章URL>" \
     --comment "<评论内容>"
   ```

5. **手动兜底（脚本失败时）**
   - 用 agent-browser 手动打开、填表、提交
   - 记录结果：
   ```bash
   python3 backlink_db.py add-submission <site_id> <project_name> 已提交 \
     --url "<文章URL>" \
     --submit-url "<你要提交的外链URL>" \
     --comment "<评论内容>" \
     --comment-id "<评论ID>" \
     --reason "手动提交成功"
   ```

---

## 注意事项

- **浏览器**：全程用 agent-browser，禁止 Hermes 内置浏览器
- **项目参数**：`--project` 和 `--submit-url` 由主人每次指定，不预设固定列表
- **失败记录**：必须写 notes，说明具体原因
- **提交证据**：博客评论要记录 `submit_url/target_url/comment_text/comment_id/result_reason`
- **日志定位**：`logs/submission.log` 仅作追加审计留痕；主数据源仍是 SQLite 的 `submissions`
- **提交后 worth 更新**：成功恢复 `worth=1` 并清空 `skip_reason`；失败只增加 `consecutive_failures`，硬障碍才降级
- **失败计数无阈值**：`consecutive_failures` 只是观察值，不自动触发 worth 降级
- **数据库备份**：迁移、批量更新 worth、手工 SQL 前先备份 `backlinks.db`
- **一站点三项目**：错开时间提交，不要同时提交三个
- **自动化绕过**：部分站点检测 headless 浏览器，`agent-browser open` 命令必须加 `--args "--disable-blink-features=AutomationControlled"`；仅设置 `AGENT_BROWSER_ARGS` 环境变量不生效，须作为 open 命令参数传入
- **Daemon 持久化陷阱**：`agent-browser close --all` 只关闭标签页/session，**不会关闭 daemon 进程**。后续 `open` 命令复用已有 daemon，`--args` 被静默忽略。必须**完整杀掉 daemon 进程**后再 open，`--args` 才会生效。每次用 `backlink_submit.py` 提交前也必须先杀 daemon，否则后续调用仍然复用旧 daemon 导致 --args 无效。
- **Daemon 卡死恢复**：`agent-browser close --all` 无效时，执行 `pkill -f agent-browser && pkill -f "Chrome for Testing"` 彻底重置
- **脚本超时降级**：`backlink_submit.py` 连续超时时，改用 SOP 第5步的子代理手动提交流程

---

## 关键文件

- `backlink_common.py`：共享迁移、状态常量、agent-browser 命令、项目视图生成
- `backlink_submit.py`：自动提交评论并写 `submissions` / 更新 worth
- `prevalidate.py`：提交前 DOM 预检，只对硬障碍降级
- `backlink_db.py`：仅保留 `stats` 和 `add-submission`；不要恢复 Excel import/export

---

## 常用命令

```bash
# 查看统计
python3 backlink_db.py stats

# 回归测试
python3 -m unittest tests/test_backlink_project.py

# 备份数据库（迁移/批量更新/手工 SQL 前）
mkdir -p backups && cp backlinks.db backups/backlinks-$(date +%Y%m%d-%H%M%S).db

# 预检 worth=1 站点（只自动标记硬障碍）
python3 prevalidate.py --project "<project_name>" --apply

# 重置 agent-browser daemon（卡死时使用）
pkill -f agent-browser && pkill -f "Chrome for Testing" && sleep 2 && echo "已重置"

# 必杀 daemon（确保 --args 生效，每次提交前执行）
kill -9 $(ps aux | grep -v grep | grep -E "agent-browser|Chrome" | awk '{print $2}') 2>/dev/null; sleep 2

# 标记 worth=0（硬性不值得，必须是站点级硬障碍）
python3 -c "
import sqlite3
db = sqlite3.connect('backlinks.db')
db.execute('UPDATE sites SET worth_submitting = 0, skip_reason = \"无 Website 字段\" WHERE id = <site_id>')
db.commit()
"

# 标记 worth=1（值得继续尝试，并清空旧 skip_reason）
python3 -c "
import sqlite3
db = sqlite3.connect('backlinks.db')
db.execute('UPDATE sites SET worth_submitting = 1, skip_reason = NULL WHERE id = <site_id>')
db.commit()
"
