# Backlink 提交管理数据库

## ER 图

```mermaid
erDiagram
    sites ||--o{ submissions : "has"
    
    sites {
        INTEGER id PK
        TEXT site_name
        TEXT site_url UNIQUE
        TEXT site_type
        INTEGER weight
        TEXT language
        TEXT category
        TEXT notes
        TEXT created_at
    }
    
    submissions {
        INTEGER id PK
        INTEGER site_id FK
        TEXT project_name
        TEXT status
        TEXT notes
        TEXT updated_at
        UNIQUE(site_id, project_name)
    }
```

---

## 关系规则

1. **一个站点可以被多个项目提交** — 一对多
2. **一个项目对一个站点只有一条提交记录** — UNIQUE(site_id, project_name)
3. **站点可以有提交记录，也可以没有**
4. **删除站点时级联删除提交记录** — ON DELETE CASCADE

---

## 数据统计

| 项目 | 数值 |
|-----|------|
| 站点总数 | 509 |
| 提交记录 | 123 |
| 追踪项目 | heicpdf.to, tryschedule.com |

### 站点分类

| 分类 | 数量 | 说明 |
|-----|------|------|
| ✅ 可自动提交 | 180 | 可通过脚本自动提交 |
| 🔐 需登录 | 32 | 需要手动登录提交 |
| 💀 已失效 | 45 | 链接失效 |
| 💰 需付费 | 1 | 需要付费 |

### 站点类型

- 搜索引擎（Yandex 等）
- 工具站（toolpilot.ai, softwareadvice.com 等）
- 博客评论 (blog_comment)
- Profile 页面 (profile)

---

## 查询示例

```sql
-- 查看所有可自动提交的站点
SELECT site_name, site_url, site_type FROM sites WHERE category = '✅ 可自动提交';

-- 查看某个项目已提交的站点
SELECT s.site_name, s.site_url, sub.status, sub.updated_at
FROM sites s
JOIN submissions sub ON sub.site_id = s.id
WHERE sub.project_name = 'heicpdf.to' AND sub.status = '已提交';

-- 查看高权重未提交的站点
SELECT s.site_name, s.site_url, s.weight
FROM sites s
LEFT JOIN submissions sub ON sub.site_id = s.id AND sub.project_name = 'heicpdf.to'
WHERE s.weight > 70 AND sub.id IS NULL
ORDER BY s.weight DESC;

-- 查看待提交的站点
SELECT s.site_name, s.site_url, s.weight, sub.status
FROM sites s
JOIN submissions sub ON sub.site_id = s.id
WHERE sub.project_name = 'heicpdf.to' AND sub.status = 'pending';
```
