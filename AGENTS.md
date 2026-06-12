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

## 三、浏览器要求

**全程必须使用 CloakBrowser！** 无论自动还是手动，无论成功还是失败，一律 CloakBrowser。
禁止使用 Hermes 内置浏览器（browser_navigate）。

```python
from cloakbrowser import launch
browser = launch(headless=True, proxy="http://127.0.0.1:7890")
```

---

## 四、提交流程（仅限 blog_comment 类型）

当前流程仅针对博客评论提交。其他类型站点（form、directory、profile、article、github、listing）暂未涉及，后续设计。

### 第一步：自动提交（首选）

自动执行：
1. CloakBrowser 打开文章页面
2. 尝试多种选择器组合找评论表单
3. 填表 → 提交
4. 检测结果（URL #comment- / 页面成功提示）
5. **自动写入数据库 + 日志** ✅

### 第二步：手动兜底（自动失败时）

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

## 五、数据库管理（backlink_db.py）

```bash
# 查看统计
python3 backlink_db.py stats

# 数据库 → Excel
python3 backlink_db.py export

# Excel → 数据库
python3 backlink_db.py import

# 手动补救
python3 backlink_db.py add-submission <site_id> <project> <status> [选项]
```

---

## 六、障碍处理

| 障碍 | 处理 |
|------|------|
| 验证码 | 填好表单，等主人过验证码 |
| 需登录 | 跳过，标记到数据库 |
| 404/失效 | 跳过，标记到数据库 |
| 需付费 | 记录费用，主人决定 |

---

## 七、注意事项

1. **禁止主动导出 Excel** — 只有主人说"导出"时才执行
2. **一站点三项目** — 错开时间提交，不要同时提交三个

---

**文档版本**: v4.1
**最后更新**: 2026-06-12
