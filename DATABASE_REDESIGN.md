# 数据库表结构调整说明

## 一、设计思路

将原来的 `submissions` 表拆分成多个项目表，一个项目一张表。

**原因：**
- 主人手动查看和更新时，直接打开对应项目表即可
- 不用每次写 WHERE project_name = xxx
- 查看更直观，操作更方便

---

## 二、表结构

### sites 表（不变）

```sql
CREATE TABLE sites (
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
```

### 项目表（每个项目一张）

```sql
CREATE TABLE <项目名> (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER,
    status TEXT,
    notes TEXT,
    result_reason TEXT,
    comment_text TEXT,
    updated_at TEXT,
    FOREIGN KEY (site_id) REFERENCES sites(id)
);
```

**表名规则：** 直接用项目 URL，点号换成下划线

| 表名 | 项目 |
|------|------|
| heicpdf_to | heicpdf.to |
| tryschedule_com | tryschedule.com |
| extractkeywords_com | extractkeywords.com |

---

## 三、字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| site_id | INTEGER | 关联 sites 表 |
| status | TEXT | 提交状态（已提交/失败/待确认等） |
| notes | TEXT | 备注 |
| result_reason | TEXT | 失败原因 |
| comment_text | TEXT | 评论原文 |
| updated_at | TEXT | 更新时间 |

---

## 四、操作示例

### 新增项目

```sql
CREATE TABLE heicpdf_to (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER,
    status TEXT,
    notes TEXT,
    result_reason TEXT,
    comment_text TEXT,
    updated_at TEXT,
    FOREIGN KEY (site_id) REFERENCES sites(id)
);
```

### 查看项目提交状态

```sql
SELECT 
    s.id,
    s.site_url,
    s.site_type,
    s.worth_submitting,
    sb.status,
    sb.notes
FROM sites s
LEFT JOIN heicpdf_to sb ON s.id = sb.site_id;
```

### 手动提交成功后写入

```sql
INSERT INTO heicpdf_to (site_id, status, notes, updated_at)
VALUES (1, '已提交', '手动提交成功', datetime('now', 'localtime'));
```

### 创建视图方便查看

```sql
CREATE VIEW view_heicpdf_to AS
SELECT 
    s.id,
    s.site_url,
    s.site_type,
    s.worth_submitting,
    sb.status,
    sb.notes,
    sb.result_reason,
    sb.comment_text
FROM sites s
LEFT JOIN heicpdf_to sb ON s.id = sb.site_id;
```

---

## 五、与原方案对比

| 方面 | 原方案（一张 submissions） | 新方案（每项目一张表） |
|------|--------------------------|----------------------|
| 表数量 | 2 张（sites + submissions） | 1 + N 张（sites + 每项目一张） |
| 查看项目 | 需要 WHERE project_name = xxx | 直接打开对应表 |
| 新增项目 | 插入记录即可 | 需要建新表 |
| 代码处理 | project_name 作为字段值 | 表名动态拼接 |
| 统计所有项目 | SELECT ... FROM submissions | 需要 UNION 多个表（实际不需要） |

**适用场景：**
- 主人手动查看和更新为主
- 每次只查看一个项目
- 新增项目频率低（一个月 2-3 次）

---

## 六、迁移步骤

1. 从原 submissions 表导出数据
2. 按项目分组，创建对应的项目表
3. 数据导入到新表
4. 删除原 submissions 表
5. 创建视图方便查看

**迁移脚本待实现。**
