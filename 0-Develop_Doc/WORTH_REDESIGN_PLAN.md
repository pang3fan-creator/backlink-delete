# Worth 重设计方案（终版）

## 一、核心定位

`worth_submitting` 从"站点是否值得提交"升级为 **"AI 与主人之间的处理责任分流状态"**。

`worth` 不再只是"值不值得"，而是回答一个问题：**这个站点，归谁管，下一步谁动手？**

---

## 二、新 worth 定义

| worth | 含义 | 归谁管 |
|-------|------|--------|
| NULL  | AI 尚未实际处理过 | AI |
| 0     | 站点级硬死亡：DNS/SSL/404/长期超时，主人和 AI 原则上都不处理 | 原则上没人管 |
| 1     | AI 当前流程无法可靠接管，转给主人处理；未来工具或策略升级后可重新评估 | 主人为主，AI 为辅 |
| 2     | AI 已验证该站点在当前流程下可自动提交，优先进入 AI 自动提交队列 | AI |

### 判 0 的硬标准

仅限站点级硬障碍：

- 页面不可访问：DNS 解析失败、SSL 证书错误、连接被拒、404/410 gone
- 长期多次超时（不是一个 timeout 就判死刑）
- 域名出售/网站已关闭/恶意软件

### 判 1 的典型场景

- 登录墙（wp-login redirect、OAuth、需要注册）
- 验证码 / reCAPTCHA / hCaptcha / Cloudflare challenge
- 有评论表单但没找到 Website/URL 字段（页面活着，留给主人判断是否有别的外链路径）
- 评论已关闭
- 脚本填表失败、提交无确认信号
- **"无 Website 字段"不再判 0，改为 worth=1**：页面活着，主人可能找到脚本没发现的字段，或有别的外链方式

### 判 2 的标准

- AI 在当前流程下完整走通：表单完整 + Website 字段存在 + 填表成功 + 提交成功
- 提交结果显示"评论待审核"或"感谢评论"等成功信号

---

## 三、worth 与 submission.status 的关系

`worth` 是**站点级**责任分流状态（`sites` 表），`submissions` 是 **project 级**尝试记录（`submissions` 表）。两者解耦：

- 评估 NULL 站点（无 project 上下文）→ 只写 `sites.worth_submitting`，不写 `submissions`
- 带着 project + submit_url 的实际提交 → 同时写 `sites.worth_submitting` 和 `submissions`

`submissions.status` 保留所有现有细分状态作为审计记录。worth 判定层面按如下映射：

| worth | 对应 submission.status | 前置条件 |
|-------|----------------------|----------|
| 0     | 已失效               | 有 project 上下文 |
| 1     | 失败 / 需登录 / 需验证码 / 待确认 / 跳过 | 有 project 上下文 |
| 2     | 已提交               | 有 project 上下文 |

`submissions.status` 继续使用完整枚举：`已提交, 待确认, 失败, 需付费, 需登录, 需验证码, 已失效, 跳过`。

---

## 四、提交优先级

### 主人指定了

无条件按主人要求执行。参数语义：

| 参数 | 作用 | 示例 |
|------|------|------|
| `--worth N` | **筛选队列**：从哪个 worth 池取站点 | `--worth 0` 从死站队列取 |
| `--force` | **绕过保护**：不管站点状态都执行提交 | `--worth 0 --force` 强制翻旧账 |

`--worth` 只管"从哪个池子捞"，`--force` 才管"要不要跳过保护"。两者独立。

### 主人未指定

默认队列**只跑 NULL/2/1，不翻 worth=0**。同时排除当前 project 已有 submission 的站点：

```sql
SELECT s.* FROM sites s
LEFT JOIN submissions sb ON s.id = sb.site_id AND sb.project_name = ?
WHERE sb.id IS NULL
  AND (s.worth_submitting IS NULL OR s.worth_submitting IN (1, 2))
ORDER BY
  CASE WHEN s.worth_submitting IS NULL THEN 0
       WHEN s.worth_submitting = 2 THEN 1
       ELSE 2 END,
  s.id
```

worth=2 只说明这个站点 AI 能提交，不代表当前 project 没交过。只有主人显式 `--worth 0 --force` 才翻旧账。

按以下优先级：

```
null > 2 > 1 > 0
```

| 优先级 | worth | 默认队列 | 如何进入 |
|--------|-------|----------|----------|
| 最高   | NULL  | ✅ 包含 | 自动 |
| 高     | 2     | ✅ 包含 | 自动 |
| 低     | 1     | ✅ 包含 | 自动 |
| 最低   | 0     | ❌ 排除 | 主人显式 `--worth 0 --force` |

| 优先级 | worth | 理由 |
|--------|-------|------|
| 最高   | NULL  | 未被处理过，需要尽快定性 |
| 高     | 2     | 已验证可自动提交，当前 project 未提交过 |
| 低     | 1     | AI 当前搞不定，但偶尔可以试试 |
| 最低   | 0     | 实在没站可投了才翻旧账（万一站点复活了） |

---

## 五、一趟结束流程

一次 `session.open()`，不重开页面，一气呵成。

**核心原则：AI 是主力，脚本是工具。** 每一步脚本先上，脚本挂了 AI 换工具/换思路接手。脚本返回结构化结果，AI orchestrator 根据结果决定下一步——AI 兜底逻辑存在于 orchestrator/SOP 层，不硬编码进 `backlink_submit.py`。

**架构分层**：AI 是主力（orchestrator），脚本是工具。

| 层 | 谁 | 干什么 |
|----|-----|------|
| orchestrator | AI | 查队列选站 → 提取文章 → 生成评论 → 调用脚本 |
| 脚本 | `backlink_submit.py` | 接收 site_id + comment → 从 DB 读单站信息 → 打开页面 → 检查 → 填表 → 提交 → 写回 DB |

脚本职责边界：
- ✅ 按 `site_id` 读单站数据（`sites.site_url` 等）并写 `submissions` + `sites.worth`
- ❌ 不负责队列选择、不负责跨站遍历、不负责生成评论、不负责做决策

orchestrator 由 AI 驱动：用 SQL 查队列、用 webfetch 提取文章、用 LLM 生成评论，最后调脚本提交。

唯一例外是第 4 步生成评论：脚本不做，AI 在调用脚本之前完成。

```
1. 打开页面
   ├── 脚本首选：CloakBrowser open(url)
   │   ├── 成功 → 继续
   │   └── 失败 → AI 接手
   │       ├── AI 用浏览器工具 / webfetch 尝试
   │       │   ├── 能打开 → 继续
   │       │   └── 也打不开 → worth=0, status=已失效, failures++, 停
   │       └── 注意：CloakBrowser 环境异常（进程崩溃、代理异常）→ 保持原值，记录运行错误
   │
2. 检测登录墙 / 验证码 / Cloudflare
   ├── 脚本首选：session.eval(JS) 检查 DOM + URL + title
   │   ├── 命中 → worth=1, status=需登录/需验证码, skip_reason=原因, failures++, 停
   │   └── 未命中 → 继续
   │
3. 提取文章内容
   ├── 脚本首选：session.get_text("body") + session.get_title()
   │   ├── 提取成功 → 继续
   │   └── 提取失败 / 内容太少 → AI 接手
   │       └── AI 用 webfetch 重拉页面 HTML 提取正文 → 继续
   │
4. 生成评论                                   ← 无脚本方案，由 AI 在调用脚本前完成
   └── AI 根据文章标题、正文、主题，生成贴合内容的中文评论
       （不提网址、不写广告词，像真实读者互动）
       → 将评论作为参数传入脚本
   │
5. 查找评论表单
   ├── 脚本首选：session.eval(JS) 用 CSS 选择器定位
   │   │   #commentform, .comment-form, form[action*="comment"]
   │   ├── 找到 → 继续
   │   └── 没找到 → AI 接手
   │       ├── AI 用浏览器工具 / webfetch 拿 HTML，正则找 <form> / textarea[name="comment"]
   │       ├── AI 手动 inspect，换策略（iframe？点"回复"才展开？）
   │       ├── AI 找到了 → 回到流程继续
   │       └── AI 也找不到 → worth=1, status=失败, skip_reason=无表单, failures++, 停
   │
6. 查找 Website 字段
   ├── 脚本首选：session.eval(JS) 用 URL_FIELD_SELECTOR 定位
   │   ├── 找到 → 继续
   │   └── 没找到 → AI 接手
   │       ├── AI 分析页面 HTML，找 input[name*="url"], input[name*="website"]
   │       ├── AI 找到了 → 回到流程继续
   │       └── AI 也找不到 → worth=1, status=失败, skip_reason=无Website, failures++, 停
   │       （不再判 0：页面活着，主人可能有别的外链路径）
   │
7. 填表 + 提交
   ├── 脚本首选：session.fill_label / fill_selector / click_text
   │   ├── 填表成功 + 提交成功（有确认信号）→ worth=2, status=已提交, failures=0, 停
   │   ├── 填表成功 + 提交无确认 → worth=1, status=待确认, skip_reason=原因, failures++, 停
   │   └── 填表失败 → AI 接手
   │       ├── AI 用浏览器工具手动填表提交
   │       │   ├── 成功 → worth=2, status=已提交, failures=0, 停
   │       │   └── 失败 → worth=1, status=失败, skip_reason=填表提交失败, failures++, 停
```

**代码层唯一依赖的浏览器运行时仍是 CloakBrowser。** AI 兜底时可使用任何可用工具（浏览器工具、webfetch、HTML 分析），但不作为项目依赖引入。

### 分工规则

| 步骤 | 脚本方案 | AI 兜底方案 |
|------|---------|------------|
| 打开页面 | CloakBrowser open() | 浏览器工具 / webfetch |
| 检测登录墙 | eval JS 检查 DOM/URL/title | 读 HTML 内容判断 |
| 提取文章 | get_text / get_title | webfetch 重拉 + 正则提取 |
| 生成评论 | **无，由 AI 调用前完成** | — |
| 查找表单 | eval JS + CSS 选择器 | 浏览器工具 / HTML 分析 / 换策略 |
| 查找 Website | eval JS + URL_FIELD_SELECTOR | 分析 HTML 找 input 字段 |
| 填表提交 | fill_label / fill_selector / click_text | 浏览器工具手动填表 |

**判断存活的口径**：脚本 + AI 两个都搞不定，才算"死了"（worth=0）。脚本挂了 AI 没尝试，不能判 0。

**重要实现约束**：流程图中"AI 接手"步骤不在 `backlink_submit.py` 内部实现。脚本返回结构化结果（如 `{"accessible": false, "reason": "timeout"}`），AI orchestrator 据此决定是否用 webfetch/浏览器工具兜底。不要把 AI fallback 硬编码进 Python 脚本。

---

## 六、状态转换矩阵

```
┌────────┬──────────────────────────────────────────────────────┐
│ 当前值 │ 本次访问结果                                          │
├────────┼──────────────────────────────────────────────────────┤
│ NULL   │ 死了 → 0, failures++（有 project 时 status=已失效）       │
│        │ 活着但卡在半路 → 1, skip_reason=原因, failures++            │
│        │ 全部走完+提交成功 → 2, failures=0（有 project 时 status=已提交）│
│        │ 环境异常不可信 → NULL(不动), 记录运行错误                   │
├────────┼──────────────────────────────────────────────────────┤
│ 0      │ 还是死的 → 0, failures++                             │
│        │ 活了但搞不定 → 1, skip_reason=原因, failures++        │
│        │ 活了+提交成功 → 2, status=已提交, failures=0          │
├────────┼──────────────────────────────────────────────────────┤
│ 1      │ 死了 → 0, status=已失效, failures++                  │
│        │ 还是搞不定 → 1(不动), failures++                     │
│        │ 提交成功 → 2, status=已提交, failures=0               │
├────────┼──────────────────────────────────────────────────────┤
│ 2      │ 死了 → 0, status=已失效, failures++                  │
│        │ 活着但搞不定 → 1, skip_reason=原因, failures++        │
│        │ 提交成功 → 2(不动), failures=0                        │
└────────┴──────────────────────────────────────────────────────┘
```

### 关键规则

- **NULL 不经过中间态**：一趟走完直接到最终值（0/1/2）
- **环境异常保持原值**：CloakBrowser 崩溃、代理异常、运行时超时等"本次环境不可信"场景，不强行改 worth。**同样适用于 worth=2：环境异常不得导致降级**
- **任何非 2 站不成功 → failures++**（值按死/活/卡分到 0/1）
- **任何站提交成功 → worth=2, failures=0**
- **2 降级：一次失败就降**（无阈值，一视同仁）。但仅限站点级原因（页面活着但登录/验证码/表单变了），环境异常不降
- **无 Website 字段 ≠ 0**：页面活着就是 worth=1，转给主人判断

---

## 七、涉及文件

### 修改

| 文件 | 改动 |
|------|------|
| `backlink_common.py` | 新 worth 常量；`apply_site_worth()` 函数；`migrate_database()` 只改 schema，不清业务数据 |
| `backlink_submit.py` | 重写为统一入口：`submit_one_site()` 一趟结束；**开头内置 worth=0 守卫**（拒绝提交，除非 `--force`）；去掉 `can_submit_site()`；worth 更新用新语义。不含 `--worth` 参数（那是 orchestrator 层概念）。文章提取由 AI orchestrator 用 webfetch 完成，不内联进脚本 |
| `evaluate_worth_cloak.py` | 适配新 worth (0/1)；**只能写 0 或 1，永远不写 2**。2 的唯一来源是 `backlink_submit.py` 真实提交成功。定位为探测/复核工具：打开页面 → 判定死活(0)/搞不定(1) |
| `tests/test_backlink_project.py` | 全量更新 worth 断言；新增转换测试、环境异常测试 |
| `AGENTS.md` | 更新 worth 定义、流程图、常用命令 |

### 新增

| 文件 | 用途 |
|------|------|
| `worth_state.py` | worth 常量 + `apply_worth()` + `worth_to_submission_status()` 映射函数 |

### 删除（本轮完成，按顺序）

| 顺序 | 文件 | 原因 |
|------|------|------|
| — | 先实现新 `backlink_submit.py` + `worth_state.py`，跑通测试 | — |
| — | AGENTS.md 全部切换到新 worth 规则 | — |
| 1 | `prevalidate.py` | 所有逻辑已合入新 `backlink_submit.py` |
| 2 | `backlink_prepare.py` | 文章提取由 AI orchestrator（webfetch）完成，脚本不再需要此能力 |
| 3 | `0-Develop_Doc/WORTH_SUBMITTING_LOGIC.md` | 旧三态过程文档，与新四态责任分流冲突 |

全部在本轮完成，不遗留到下个版本。

---

## 八、核心函数

### `backlink_submit.py`

```python
def submit_one_site(
    project: str,
    submit_url: str,
    site_id: str,
    comment: str,            # AI 在调用前已生成
    name: str = DEFAULT_NAME,
    email: str = DEFAULT_EMAIL,
    force: bool = False,     # 绕过 worth=0 保护
) -> dict:
    """
    一趟结束：
    1. 读 sites.worth_submitting → 如果为 0 且 force=False → 直接拒绝
    2. 要打开的页面 URL 从 sites.site_url 读取
    3. 打开 → 检查 → 填表 → 提交 → 写回 DB
    
    --worth 参数不属于本脚本；队列筛选是 AI orchestrator 层通过 SQL 完成的。
    
    返回:
        {
            "worth": 0|1|2,
            "status": "已提交"|"待确认"|"失败"|"需登录"|...,
            "comment_id": str|None,
            "error": str|None,
            "skip_reason": str|None,
            "failures": int,
        }
    """
```

### `worth_state.py`

```python
WORTH_DEAD = 0       # 站点级硬死亡
WORTH_AI_CANT = 1    # AI 当前无法接管，转主人
WORTH_AI_CAN = 2     # AI 已验证可自动提交

def apply_worth(conn, site_id, worth, skip_reason=None,
                failures_increment=0, failures_reset=False) -> None:
    ...

def worth_to_status(worth: int, reason: str = "") -> str:
    """0→已失效, 2→已提交, 1→根据 reason 选 需登录/需验证码/失败/待确认"""
```

---

## 九、数据迁移

### schema 迁移（`migrate_database()` 自动执行）

- 确保 `sites.consecutive_failures` 列存在
- 确保 `submissions` 表 CHECK 约束包含所有状态枚举
- 确保项目只读视图存在

### 业务数据迁移（一次性手工操作）

```sql
-- 重启 worth：所有站点恢复 NULL，清空旧评估结果
UPDATE sites SET worth_submitting = NULL, skip_reason = NULL, consecutive_failures = 0;
```

**此 SQL 不作为 `migrate_database()` 的一部分自动执行。** 由操作者按需手工运行。

---

## 十、测试计划

| # | 测试用例 | 预期 |
|---|---------|------|
| 1 | NULL 站点 DNS 失败 → AI 也打不开 | worth=0, status=已失效, failures=1 |
| 2 | NULL 站点有表单但缺 Website 字段 | worth=1, status=失败, skip_reason 写入 |
| 3 | NULL 站点完整成功路径 | worth=2, status=已提交, failures=0 |
| 4 | worth=2 提交失败 | worth=1, status=失败, failures++ |
| 5 | worth=0 重新可访问 | worth=1 或 2 |
| 6 | worth=1 提交成功 | worth=2, status=已提交, failures=0 |
| 7 | 多次失败 → failures 累加 | 正确累加 |
| 8 | 成功后 failures 清零 | 归零 |
| 9 | `submit_one_site()` worth=0 守卫：force=False 拒绝，force=True 放行 | force=False→拒绝提交, force=True→正常执行 |
| 10 | CloakBrowser 环境异常 | worth 保持原值, 记录运行错误（worth=2 不降级） |
| 11 | worth=0 → submission.status=已失效 | 正确映射 |
| 12 | worth=1 → submission.status=需登录/失败 等 | 根据 reason 正确选择 |
| 13 | worth=2 → submission.status=已提交 | 正确映射 |
| 14 | submission 表保留所有细分状态 | CHECK 约束完整 |
| 15 | `migrate_database()` 不清空业务数据 | worth 值不变 |

---

## 十一、功能验证清单

- [ ] 所有文件 `python3 -m py_compile` 通过
- [ ] `python3 -m unittest tests.test_backlink_project -v` 全部通过
- [ ] `migrate_database()` 不改变现有 worth 值
- [ ] 一个 NULL 站点走通完整一趟结束流程（NULL→2）
- [ ] worth=2 一次失败即降为 1
- [ ] 无 Website 字段不再判 0，判 1
- [ ] `prevalidate.py` 和 `backlink_prepare.py` 已删除
- [ ] AGENTS.md 内容与新设计完全一致（无旧 worth=1 定义、无 prevalidate 命令、无旧 WORTH_SUBMITTING_LOGIC.md 引用）
- [ ] `submissions.status` CHECK 约束包含全部枚举值
