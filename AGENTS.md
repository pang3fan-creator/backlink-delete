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

## 三、脚本说明

### 脚本职责

| 脚本 | 职责 | 说明 |
|------|------|------|
| `backlink_submit.py` | 提交评论 + 自动记录 | 主流程，提交后自动写入数据库和日志 |
| `backlink_db.py` | 数据库管理 | Excel 同步、统计、手动补救 |

### backlink_submit.py（主流程）

```bash
python3 backlink_submit.py --project <项目> --site-id <ID> --url "文章URL" --comment "评论内容"
```

**参数**：
- `--project`: extractkeywords / tryschedule / heicpdf
- `--site-id`: 站点 ID（从数据库获取）
- `--url`: 文章 URL
- `--comment`: 评论内容

**自动执行**：
1. CloakBrowser 打开页面
2. 填写表单、提交评论
3. 检查结果（成功/失败）
4. 自动写入数据库 + 日志

### backlink_db.py（数据库管理）

```bash
# 查看统计
python3 backlink_db.py stats

# 数据库 → Excel
python3 backlink_db.py export

# Excel → 数据库
python3 backlink_db.py import

# 手动补救（正常流程不需要）
python3 backlink_db.py add-submission <site_id> <project> <status> [选项]
```

---

## 四、障碍处理

| 障碍 | 处理 |
|------|------|
| 验证码 | 填好表单，等主人过验证码 |
| 需登录 | 跳过，标记到数据库 |
| 404/失效 | 跳过，标记到数据库 |
| 需付费 | 记录费用，主人决定 |

---

## 五、注意事项

1. **禁止主动导出 Excel** — 只有主人说"导出"时才执行
2. **一站点三项目** — 错开时间提交，不要同时提交三个

---

**文档版本**: v4.0
**最后更新**: 2026-06-12
