# worth_submitting 字段逻辑说明

## 一、字段定义

`worth_submitting` 只表示站点是否值得继续尝试，不表示自动化脚本本次是否跑通。

| 值 | 含义 | 说明 |
|---|------|------|
| NULL | 未评估 | 入库初始状态，下次继续评估 |
| 1 | 值得继续尝试 | 包含自动可提交、人工可能可处理、历史成功过 |
| 0 | 硬性不值得 | 必须写 `skip_reason`，表示站点级硬障碍 |

不使用 `worth=2`。成功历史、连续失败等观察信息使用独立字段记录。

---

## 二、worth=0 判定标准

`worth=0` 只能用于站点级硬障碍，不能用于表示“一次预检失败”或“一次自动提交失败”。

允许标记 `worth=0` 的情况：

| 条件 | 说明 |
|------|------|
| 404 / 页面不存在 | 页面明确不存在 |
| 域名失效 / 无法解析 | DNS 或域名解析失败 |
| SSL 证书错误 | 证书问题导致页面不可用 |
| 长期超时 / 多次超时 | 多次尝试仍长期无响应 |
| 网站已关闭 | 页面显示网站关闭、域名出售等 |
| 明确拒绝外部链接 | 页面明确说明不接受外部链接 |
| 无 Website/URL 字段 | 评论表单没有可留下外链的字段 |
| 纯垃圾/恶意站 | 赌博、恶意软件、明显内容农场等 |

以下情况不是 `worth=0`：

- 需要登录
- 有验证码
- Cloudflare / challenge
- 自动化没有找到评论表单
- 表单结构复杂或 SPA 自动化填不了
- 主题相关性不确定
- 需要付费

这些情况应记录到 `submissions.status/result_reason`，但不轻易降级站点 worth。

---

## 三、提交后更新规则

### 自动提交成功

成功提交是最高优先级证据：

- `worth_submitting = 1`
- `skip_reason = NULL`
- `consecutive_failures = 0`

即使站点原本是 `worth=0` 或 `NULL`，成功后也恢复为 `worth=1`。

### 自动提交失败

一次失败不足以证明站点不值得：

- 普通失败：保持原 `worth_submitting` 不变，只增加 `consecutive_failures`
- 硬障碍失败：`worth_submitting = 0`，写入 `skip_reason`
- 失败原因必须写入 `submissions.status/result_reason`

---

## 四、预检脚本规则

`prevalidate.py` 保留为提交前安全检查，但 `--apply` 只对硬障碍写 `worth=0`。

预检失败处理：

| 失败原因 | 操作 |
|---------|------|
| 404 / DNS / SSL / 明确无 Website 字段等硬障碍 | 写 `worth=0 + skip_reason` |
| 登录墙 / 验证码 / Cloudflare / 自动化找不到字段 / 表单复杂 | 保留 worth，不降级 |

预检脚本的职责是减少无效自动提交，不是永久淘汰站点。

---

## 五、辅助字段

### consecutive_failures

**类型：** `INTEGER DEFAULT 0`

**作用：** 观察自动化连续失败次数，不直接等同于 `worth=0`。

更新规则：

- 自动提交成功：清零
- 自动提交失败：加 1
- 是否降级为 `worth=0` 仍由失败原因是否属于硬障碍决定

---

## 六、数据库迁移

只做增量迁移，不重建 `sites` 表，不清空历史数据：

```sql
ALTER TABLE sites ADD COLUMN consecutive_failures INTEGER DEFAULT 0;
```

实际迁移由 `backlink_common.migrate_database()` 自动补齐字段。

禁止执行全量重置：

```sql
-- 不要执行
UPDATE sites SET worth_submitting = NULL, consecutive_failures = 0, skip_reason = NULL;
```

原因：这会丢失已经评估出的硬障碍和历史 `skip_reason`。

---

## 七、关键原则

1. `worth=0` 只标记硬障碍，不能表示自动化失败。
2. 预检不轻易淘汰站点，只对硬障碍降级。
3. 自动提交成功可以覆盖旧判断，恢复为 `worth=1`。
4. 自动提交失败默认只记录本次结果，不立刻降级。
5. 宁可保留给主人判断，也不要因为一次脚本失败错杀站点。
