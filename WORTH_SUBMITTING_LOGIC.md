# worth_submitting 字段逻辑说明

## 一、字段定义

| 值 | 含义 | 谁来标记 | 说明 |
|---|------|---------|------|
| NULL | 未评估，不知道能不能提交 | 默认 | 入库时的初始状态 |
| 0 | 网站本身有问题，去了也是浪费 | 提交脚本 | 死站/坏站，不再尝试 |
| 1 | AI 搞不定，主人可能能搞定 | 提交脚本 | 不确定状态，留给主人判断 |
| 2 | 已成功提交过，证明可提交 | 提交脚本 | 成功后才标记，失败多次会降级 |

---

## 二、判定标准

### worth=0（绝对不值得，去了也是浪费）

以下情况标记为 worth=0：

| 条件 | 说明 |
|------|------|
| 404 / 页面不存在 | HTTP 状态码 404 |
| 域名失效 / 无法解析 | DNS 解析失败 |
| SSL 证书错误 | HTTPS 证书无效 |
| 长期超时 / 无响应 | 多次尝试无果 |
| 网站已关闭 | 页面显示"网站已关闭"、"域名出售"等 |
| 明确拒绝外部链接 | 页面有文字说明"不接受外部链接"等 |
| 纯垃圾/恶意站 | 赌博、恶意软件、内容农场等 |

**注意：**
- "需要登录"不是 worth=0，主人可以自己登录
- "有验证码"不是 worth=0，主人可以手动填
- "主题不相关"不是 worth=0，由主人自己判断
- "需要付费"不是 worth=0，由主人自己决定是否付费

### worth=2（100% 能成功）

以下情况标记为 worth=2：

| 条件 | 说明 |
|------|------|
| 实际提交成功过 | 提交脚本报成功后才标记 |

**注意：**
- worth=2 不是"永久通行证"
- 如果连续 3 个项目都提交失败，会降级为 worth=1
- 需要用实际提交结果来验证，不能靠预测

### worth=1（兜底状态）

不在 worth=0 和 worth=2 的情况，都归为 worth=1：

- 需要登录
- 有验证码
- SPA 表单填不了
- 网站结构复杂
- 不确定的情况
- AI 搞不定但主人可能能搞定

---

## 三、提交逻辑流程

```
从数据库筛选 worth != 0 且该项目未提交的站点
                    │
                    ▼
               打开页面
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
      死站/坏站   提交成功    提交失败
         │          │          │
         ▼          ▼          ▼
     worth=0    worth=2    见下方详细逻辑
```

### 详细逻辑

#### 原始 worth=NULL

| 提交结果 | 操作 |
|---------|------|
| 死站（404/域名失效等） | worth=0 |
| 成功 | worth=2, consecutive_failures=0 |
| 失败 | worth=1 |

#### 原始 worth=1

| 提交结果 | 操作 |
|---------|------|
| 成功 | worth=2, consecutive_failures=0 |
| 失败 | worth=1（不变） |

#### 原始 worth=2

| 提交结果 | 操作 |
|---------|------|
| 成功 | worth=2, consecutive_failures=0 |
| 失败 | consecutive_failures += 1，若 >= 3 则 worth=1 |

---

## 四、辅助字段

### consecutive_failures（连续失败次数）

**类型：** 整数，默认 0

**作用：** 记录 worth=2 的站点连续提交失败的次数

**更新规则：**
- 提交成功 → `consecutive_failures = 0`
- 提交失败 → `consecutive_failures += 1`
- 当 `consecutive_failures >= 3` → worth 降级为 1

**意义：**
- worth=2 的站点一次失败不降级（可能是临时问题）
- 连续 3 个项目都失败才降级，说明网站可能改版或加了限制

---

## 五、关键原则

1. **worth=0 只标记"硬障碍"** — 网站本身有问题，主人去也是浪费
2. **worth=1 是默认兜底** — 不确定的情况都归这里，不让 AI 随便判"不行"
3. **worth=2 靠事实说话** — 成功过才算，失败多了会降级
4. **提交脚本只标记结果** — 不做"预判"，打开页面看看才知道
5. **宁可留着让主人看，不要错杀** — 不确定就归 worth=1

---

## 六、脚本职责

| 脚本 | 职责 | 状态 |
|------|------|------|
| `backlink_submit.py` | 提交外链 + 更新 worth 和 consecutive_failures | 保留，需修改 |
| `prevalidate.py` | 预检查站点 | **删除**（逻辑合并到提交脚本） |
| `backlink_prepare.py` | 提取文章内容（用于 blog_comment） | 可选保留或删除 |
| `backlink_db.py` | 数据库操作 | 保留 |

---

## 七、前置步骤

在实施新逻辑之前，需要先完成以下数据库操作：

### 1. 新增字段

```sql
ALTER TABLE sites ADD COLUMN consecutive_failures INTEGER DEFAULT 0;
```

### 2. 重置现有数据

之前 worth_submitting 的值是按旧逻辑标记的，不适用于新规则。需要重置：

```sql
UPDATE sites SET worth_submitting = NULL, consecutive_failures = 0, skip_reason = NULL;
```

**说明：**
- worth_submitting 重置为 NULL，让提交脚本按新逻辑重新标记
- consecutive_failures 初始化为 0
- skip_reason 清空，旧的原因不再适用

---

## 八、数据库改动

### 字段约束

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| worth_submitting | INTEGER | CHECK (worth_submitting IN (0, 1, 2)) | 只能是 NULL、0、1、2 |
| consecutive_failures | INTEGER | CHECK (consecutive_failures >= 0) | 非负整数 |
| skip_reason | TEXT | — | worth=0 时的原因说明 |

### 完整迁移脚本

SQLite 不支持直接 ALTER TABLE 加 CHECK 约束，需要重建表：

```sql
-- 1. 创建新表（带约束）
CREATE TABLE sites_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
    site_type TEXT,
    weight INTEGER,
    notes TEXT,
    created_at TEXT,
    worth_submitting INTEGER DEFAULT NULL CHECK (worth_submitting IN (0, 1, 2)),
    skip_reason TEXT,
    consecutive_failures INTEGER DEFAULT 0 CHECK (consecutive_failures >= 0)
);

-- 2. 迁移数据
INSERT INTO sites_new SELECT id, site_url, site_type, weight, notes, created_at, NULL, NULL, 0 FROM sites;

-- 3. 删除旧表
DROP TABLE sites;

-- 4. 重命名
ALTER TABLE sites_new RENAME TO sites;
```

**说明：**
- 迁移时 worth_submitting 设为 NULL，skip_reason 设为 NULL，consecutive_failures 设为 0
- CHECK 约束确保 worth_submitting 只能是 0、1、2 或 NULL
- CHECK 约束确保 consecutive_failures 是非负整数
