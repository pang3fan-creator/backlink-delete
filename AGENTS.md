# Backlink 提交 SOP

> 素贞主导的自动化提交流程：流程由素贞控制，步骤借助小工具辅助，效率最大化

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

## 二、提交流程标准化

> **工作哲学**：流程由素贞控制，步骤借助小工具辅助。机械性步骤（记录、提交）用脚本，需要理解的步骤（读文章、写评论）素贞亲自做。

### 可用工具箱

| 工具 | 用途 | 类型 |
|------|------|------|
| `bl.py` | 数据库记录、导出、统计 | 脚本 |
| `log_submission.py` | 日志文件记录 | 脚本 |
| `wp_comment.py` | 生成 WordPress 评论提交 JS 代码 | 脚本 |

### 类型 A：博客评论（WordPress）✅ 已验证

**最适合素贞操作，无验证码，成功率最高。**

#### 标准工作流

| 步骤 | 操作 | 方式 |
|------|------|------|
| 1️⃣ | 用 web_extract 读文章内容 | 素贞手动 |
| 2️⃣ | 根据文章生成评论 + 锚文本 | 素贞手动 |
| 3️⃣ | 用 browser_navigate 打开文章，在 Console 跑通用 JS | 素贞手动（可封装模板） |
| 4️⃣ | 确认 URL 跳转到 `#comment-XXX` | 素贞检查 |
| 5️⃣ | 数据库记录：`python3 bl.py add-submission ...` | 脚本 |
| 6️⃣ | 日志记录：`python3 log_submission.py --site ... --project ... --url ... --comment ... --result ...` | 脚本 |

#### 通用 JS 一键提交

```javascript
// === WordPress 博客评论一键提交 ===
document.getElementById('author').value = 'Stefan M.';
document.getElementById('email').value = 'pang3fan@gmail.com';
document.getElementById('url').value = 'https://tryschedule.com';
// ↑ Website 字段必须填！这是外链的核心目的
document.getElementById('comment').value = '【素贞按文章内容生成的评论】';
document.getElementById('submit').click();
```

**🚨 关键提醒**：
- **Website 字段必须填！** 宁可被 Akismet 拦截，不能为了防拦而不填
- 正文自然植入锚文本关键词 → 加深用户印象
- **两个都给**：Website 链接 + 正文关键词，双管齐下

#### 验证是否成功

检查 URL 是否变为 `文章URL#comment-数字`。如果是，说明提交成功。如果表单被清空但 URL 没变，说明被 Akismet 拦截了（静默过滤），换下一篇。

---

### 类型 B：传统目录站点 ⚠️ 有验证码

**通常有 reCAPTCHA 或图片验证码，素贞无法独立完成。**

| 障碍 | 处理方式 |
|------|---------|
| reCAPTCHA | 素贞填好表单后，需主人点击验证再提交 |
| 图片验证码 | 素贞截图，主人告诉验证码数字 |
| 免费提交 | 审核周期长（8-10周），但可以试试 |
| 付费提交 | 需主人决定是否付费 |

**素贞做**：填好表单所有字段，等主人过验证码
**主人做**：帮忙点 reCAPTCHA 或告诉图片验证码

---

### 类型 C：AI 工具目录 / 需登录站点 🔐

**通常需要注册或 Google 登录，主人提供账号后可尝试。**

| 配置 | 值 |
|------|-----|
| 邮箱 | pang3fan@gmail.com |
| 登录方式 | Google 登录优先 |
| 验证码 | 会发到 Gmail，素贞自动读取填入 |

---

### 类型 D：已失效 / 需付费 ❌

| 分类 | 处理方式 |
|------|---------|
| 💀 失效（404/关闭） | 跳过，标记到数据库 |
| 💰 需付费 | 记录费用信息，主人决定 |

---

### 提交后记录（双轨制）

**两条线记录，用途不同：**

| 记录位置 | 用途 | 保留周期 |
|----------|------|----------|
| **数据库** | 避免重复提交，长期统计 | 永久 |
| **日志文件** | 追溯提交过程，检查网址是否填写 | 主人定期检查后手动清理 |

**数据关联**：
- 查站点状态 → 数据库
- 查详细信息（近期） → 日志文件
- 查详细信息（久远） → 日志已删除，以数据库为准

---

#### 1. 数据库记录

```bash
python3 bl.py add-submission <site_id> <project> <status> [--notes "备注"]
```

**状态定义**（禁止自定义，数据库有 CHECK 约束）：
- `已提交` — 表单递交成功，操作无失误。站长是否审核通过由邮件追踪
- `失败` — 表单提交失败/报错/无法填写
- `需付费` — 需要付费才能提交，需主人确认
- `需登录` — 需要注册账号，需主人提供账号后提交

---

#### 2. 日志文件记录

**位置**：`logs/submission.log`
**工具**：`log_submission.py`

**每次提交调用**：
```bash
python3 log_submission.py \
  --site "https://example.com/article" \
  --project "tryschedule" \
  --url "https://tryschedule.com" \
  --name "Stefan M." \
  --email "pang3fan@gmail.com" \
  --comment "评论内容..." \
  --result "成功" \
  --comment-id "12345"
```

**日志用途**：
- 主人定期检查，确认网址是否正确填写
- 追溯某次提交的具体内容
- 检查后主人可手动清理

---

## 三、验证机制

### 每日邮件检查（6:00 任务）

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
1. 每日 6:00 读取 Gmail（过去 12 小时窗口）
2. 搜索关键词：站点名 + 项目名
3. 提取审核结果
4. 更新数据库状态
5. 如需人工处理 → 通知主人
```

---

## 四、站点分类处理

| 分类 | 说明 | 处理方式 |
|------|------|---------|
| ✅ 可提交 | 表单简单，无验证码 | 素贞主导，工具辅助提交 |
| 🔐 需登录 | 需注册账号 | 跳过，标记到数据库。主人可手动处理 |
| 💰 需付费 | 收费提交 | 记录费用信息，主人决定是否付费 |
| 💀 已失效 | 404/关闭 | 跳过，标记到数据库 |
| 📎 需上传 | 要上传 Logo | 准备 Logo 文件后提交 |

---

## 五、障碍处理

| 障碍 | 说明 | 解决方案 |
|------|------|---------|
| 🛡️ Turnstile | Cloudflare 人机验证 | 需主人点击验证 |
| 🤖 reCAPTCHA | Google 人机验证 | 需主人点击验证 |
| 🔐 需登录 | 需注册账号 | 跳过，标记到数据库 |
| 📎 需上传 | 必须上传图片 | 准备 Logo 文件 |
| ❌ 服务器错误 | 后端配置问题 | 无法解决，跳过 |

---

## 六、常用命令

```bash
# 查看提交统计
python3 bl.py stats

# 导出 Excel 查看
python3 bl.py export

# 从 Excel 导入更新
python3 bl.py import

# 添加数据库提交记录
python3 bl.py add-submission <site_id> <project> <status> [--notes "备注"]

# 添加日志提交记录
python3 log_submission.py --site <站点URL> --project <项目名> --url <提交网址> --comment <评论内容> --result <结果>
```

---

## 七、注意事项

1. **邮箱千万别落下** — pang3fan@gmail.com
2. **博客评论必须读文章** — 生成相关内容，自然插入链接
3. **一站点三项目** — 发现可提交站点，立即为三个项目都提交
4. **Website 字段必须填！** 这是外链的核心目的。日志文件记录以备主人追溯检查
5. **记录详细** — 失败要记录原因，方便后续优化
6. **定期验证** — 通过邮件追踪审核结果

---

**文档版本**: v2.1
**最后更新**: 2026-06-03
