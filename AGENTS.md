# Backlink 提交 SOP

> 素贞使用 CloakBrowser 提交外链的操作手册

---

## 一、标准信息（必填）

**配置文件**：`project-config.json`

### 统一联系方式

| 字段 | 值 |
|------|-----|
| **邮箱** | pang3fan@gmail.com |
| **用途** | 接收审核通知、确认邮件、站长回复 |

### 三个项目标准信息

| 项目 | 名称 | 域名 | 一句话描述 |
|------|------|------|-----------|
| extractkeywords | extractkeywords | extractkeywords.com | Free online keyword extraction tool |
| tryschedule | tryschedule | tryschedule.com | Free online schedule builder and planner |
| heicpdf | heicpdf | heicpdf.to | Free online HEIC to PDF converter |

**标签**：工具类、免费、在线工具

---

## 二、提交 SOP

### 验证码自动处理

遇到需要邮箱验证码的情况：
1. 验证码会发送到 `pang3fan@gmail.com`
2. 素贞自动读取 Gmail 获取验证码
3. 填入验证码继续提交
4. 结果：`已提交` 或 `失败`

**不需要通知主人，全程自动处理。**

### 提交时

| 站点类型 | 策略 | 必填字段 |
|---------|------|---------|
| **目录站点** | 使用标准模板 | name, url, email, description |
| **AI工具目录** | 强调免费+功能 | name, url, email, description, tags |
| **博客评论** | **必须读文章**，生成相关评论，自然插入链接 | name, email, comment, url |
| **搜索引擎提交** | 简洁填写 | url, email |

### 博客评论特殊处理

```python
# 1. 先读取文章内容
article_title = page.title()
article_content = page.content()

# 2. 根据文章生成相关评论
# 3. 自然插入链接（不要硬广）
# 4. 示例：
# "Great insights on [文章主题]! I found this particularly useful for [具体点]. 
#  By the way, I've been using [工具名] for [相关用途], highly recommend checking it out."
```

### 提交后记录

```bash
# 记录到数据库
python3 bl.py add-submission <site_id> <project> <status> [--notes "备注"]
```

**状态定义（禁止自定义，数据库有 CHECK 约束）**：
- `已提交` — 表单递交成功，操作无失误。站长是否审核通过由邮件追踪
- `失败` — 表单提交失败/报错/无法填写
- `需付费` — 需要付费才能提交，需主人确认
- `需登录` — 需要注册账号，需主人提供账号后提交

---

## 三、验证机制

### 每日邮件检查（6:30 任务）

素贞每天早上读 Gmail，**特别关注**：

| 关键词 | 含义 | 后续动作 |
|--------|------|---------|
| approved, accepted, listed | 外链已通过 | 标记为「✅ 已收录」 |
| rejected, declined | 外链被拒绝 | 记录原因，分析问题 |
| pending, waiting | 待审核 | 等待后续通知 |
| verification, confirm | 需要验证 | 点击验证链接 |
| link required | 需要反向链接 | 告知主人决定 |

### 验证流程

```
1. 每日 6:30 读取 Gmail
2. 搜索关键词：站点名 + 项目名
3. 提取审核结果
4. 更新数据库状态
5. 如需人工处理 → 通知主人
```

---

## 四、站点分类处理

| 分类 | 说明 | 处理方式 |
|------|------|---------|
| ✅ 可自动提交 | 表单简单，无验证码 | CloakBrowser 自动提交 |
| 🔐 需登录 | 需注册账号 | 主人提供账号后手动提交 |
| 💰 需付费 | 收费提交 | 主人决定是否付费 |
| 💀 已失效 | 404/关闭 | 跳过 |
| 📎 需上传 | 要上传 Logo | 准备 Logo 文件后提交 |

---

## 五、障碍处理

| 障碍 | 说明 | 解决方案 |
|------|------|---------|
| 🛡️ Turnstile | Cloudflare 人机验证 | 需主人点击验证 |
| 🤖 reCAPTCHA | Google 人机验证 | 需主人点击验证 |
| 🔐 需登录 | 需注册账号 | 主人提供账号 |
| 📎 需上传 | 必须上传图片 | 准备 Logo 文件 |
| ❌ 服务器错误 | 后端配置问题 | 无法解决，跳过 |

---

## 六、常用命令

```bash
# 导出 Excel 查看
python3 bl.py export

# 从 Excel 导入更新
python3 bl.py import

# 查看提交统计
python3 bl.py stats

# 添加提交记录
python3 bl.py add-submission <site_id> <project> <status>
```

---

## 七、注意事项

1. **邮箱千万别落下** — pang3fan@gmail.com
2. **博客评论必须读文章** — 生成相关内容，自然插入链接
3. **一站点三项目** — 发现可提交站点，立即为三个项目都提交
4. **记录详细** — 失败要记录原因，方便后续优化
5. **定期验证** — 通过邮件追踪审核结果

---

**文档版本**: v2.0  
**最后更新**: 2026-06-01
