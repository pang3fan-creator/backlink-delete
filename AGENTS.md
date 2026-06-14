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
2. **Website 字段必须填！** 这是外链的唯一来源
3. **评论正文不带网址** — 专注生成优质评论，更自然，通过率更高
4. 外链本质是宣传，删不删是站长的事，先提交再说
5. **先评估再提交** — 不值得的站点标记后跳过，不浪费时间

---

## 三、站点评估标准

提交前评估站点是否值得，避免浪费时间。

### 评估维度

| 维度 | 值得 (1) | 不值得 (0) |
|------|----------|------------|
| **评论功能** | 有标准评论表单且能提交成功 | 无评论/评论区关闭/Jetpack iframe/提交失败 |
| **网站合法性** | 正常网站 | 博彩/成人/违法内容（会对自身网站造成负面影响） |
| **SPAM 检查** | 正常内容 | 垃圾网站（满屏随机链接、关键词堆砌、链接农场） |

### SPAM 判断标准

打开网站后检查：

| 特征 | 说明 |
|------|------|
| ❌ 满屏随机链接 | 评论区全是 `best casino online`、`cheap viagra` 之类的垃圾链接 |
| ❌ 关键词堆砌 | 内容无意义，全是重复关键词 |
| ❌ 链接农场 | 整个网站就是为了堆外链而存在 |
| ❌ 内容农场 | 低质量 AI 生成内容，无实际价值 |
| ✅ 正常网站 | 有真实内容、真实用户互动 |

### 说明

- **DR 权重不考虑** — 新网站没资格挑挑拣拣
- **主题相关性不考虑** — 能加外链就不错了
- **验证门槛不考虑** — 主人手动可能成功，需主人自己判断
- **网站活跃度不考虑** — 不作为参考

### 评估结论

| 结论 | worth_submitting | 后续处理 |
|------|------------------|----------|
| **值得** | 1 | 提交外链 |
| **不值得** | 0 | 跳过，不提交 |
| **待评估** | NULL | 默认值，需要判断 |

### 更新评估字段

```bash
# 标记为值得
python3 -c "
import sqlite3
db = sqlite3.connect('backlinks.db')
db.execute('UPDATE sites SET worth_submitting = 1 WHERE id = <site_id>')
db.commit()
"

# 标记为不值得
python3 -c "
import sqlite3
db = sqlite3.connect('backlinks.db')
db.execute('UPDATE sites SET worth_submitting = 0 WHERE id = <site_id>')
db.commit()
"
```

---

## 四、浏览器要求

**全程必须使用 CloakBrowser！** 无论自动还是手动，无论成功还是失败，一律 CloakBrowser。
禁止使用 Hermes 内置浏览器（browser_navigate）。

```python
from cloakbrowser import launch
browser = launch(headless=True, proxy="http://127.0.0.1:7890")
```

---

## 五、提交流程（仅限 blog_comment 类型）

当前流程仅针对博客评论提交。其他类型站点（form、directory、profile、article、github、listing）暂未涉及，后续设计。

### 第一步：评估站点（新增）

打开站点前先判断：
1. 查看数据库中的 `weight`（DR 权重）
2. 用 CloakBrowser 快速打开页面
3. 检查：评论功能是否存在？网站是否活跃？
4. 更新 `worth_submitting` 字段
5. 不值得 → 跳过，下一个

### 第二步：自动提交（首选）

自动执行：
1. CloakBrowser 打开文章页面
2. 尝试多种选择器组合找评论表单
3. 填表 → 提交
4. 检测结果（URL #comment- / 页面成功提示）
5. **自动写入数据库 + 日志** ✅

### 第三步：手动兜底（自动失败时）

用 CloakBrowser 亲自查看和处理，提交成功后手动记录：

**超时** → CloakBrowser 再试一次
- 能打开 → 找表单 → 填表提交 → 记录 ✅
- 打不开 → 标记失败，跳过

**找不到评论表单** → CloakBrowser 查看
- 有表单（选择器不同）→ 用 page.evaluate 动态找 → 提交 → 记录 ✅
- Jetpack/iframe → 跳过
- 评论区已关闭 → 标记失败，跳过

**提交成功但未确认** → CloakBrowser 看页面
- 有成功提示 → 标记已提交 ✅
- 确实没成功 → 标记失败

**Cloudflare / 需登录** → 跳过

手动记录命令：
```bash
python3 backlink_db.py add-submission <site_id> <项目域名> 已提交 \
  --url "<项目域名>" \
  --comment "评论内容" \
  --comment-id "评论ID"
```

---

## 六、数据库管理（backlink_db.py）

```bash
# 查看统计
python3 backlink_db.py stats

# 数据库 → Excel
python3 backlink_db.py export

# Excel → 数据库
python3 backlink_db.py import

# 手动补救
python3 backlink_db.py add-submission <site_id> <project> <status> [选项]

# 标记站点值得/不值得
python3 -c "
import sqlite3
db = sqlite3.connect('backlinks.db')
db.execute('UPDATE sites SET worth_submitting = ? WHERE id = ?', (1或0, site_id))
db.commit()
"
```

---

## 七、障碍处理

| 障碍 | 处理 |
|------|------|
| 验证码 | 填好表单，等主人过验证码 |
| 需登录 | 跳过，标记到数据库 |
| 404/失效 | 跳过，标记到数据库 |
| 需付费 | 记录费用，主人决定 |

---

## 八、注意事项

1. **禁止主动导出 Excel** — 只有主人说"导出"时才执行
2. **一站点三项目** — 错开时间提交，不要同时提交三个
3. **先评估再提交** — 查看 worth_submitting，不值得的直接跳过

---

**文档版本**: v5.0
**最后更新**: 2026-06-14
