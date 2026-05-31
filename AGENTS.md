# Backlink 提交指南

> 素贞使用 CloakBrowser 提交外链的操作手册

---

## 一、项目概述

**目标**：为主人的多个网站项目提交外链，提升 SEO 权重。

**数据库**：`backlinks.db` — 所有站点和提交记录

**工具**：CloakBrowser（绕过基础反爬检测）

---

## 二、快速开始

### 1. 查看待提交站点

```bash
# 查看可自动提交的站点
python3 bl.py export  # 导出 Excel 查看

# 或直接查询数据库
python3 -c "
import sqlite3
conn = sqlite3.connect('backlinks.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT site_name, site_url, weight FROM sites 
    WHERE category = \"✅ 可自动提交\" 
    ORDER BY weight DESC NULLS LAST LIMIT 10
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} (权重: {row[2]})')
conn.close()
"
```

### 2. 提交一个站点

```python
from cloakbrowser import launch

browser = launch(headless=True, proxy="http://127.0.0.1:7890")
page = browser.new_page()
page.goto("https://example.com/submit")
# 填表、提交...
browser.close()
```

### 3. 记录提交结果

```bash
# 更新数据库
python3 bl.py add-submission <site_id> <project_name> <status>
```

---

## 三、站点分类

| 分类 | 说明 | 处理方式 |
|------|------|---------|
| ✅ 可自动提交 | 表单简单，无验证码 | CloakBrowser 自动提交 |
| 🔐 需登录 | 需注册账号 | 主人提供账号后手动提交 |
| 💰 需付费 | 收费提交 | 主人决定是否付费 |
| 💀 已失效 | 404/关闭 | 跳过 |
| 📎 需上传 | 要上传 Logo | 准备 Logo 文件后提交 |

---

## 四、提交流程

### 标准流程

```
1. 预检查 → 确认站点可访问
2. 打开页面 → CloakBrowser 访问提交页
3. 识别表单 → 找到输入字段
4. 填写信息 → 使用项目模板数据
5. 处理验证码 → Turnstile/reCAPTCHA 无法自动通过
6. 提交表单 → 点击提交按钮
7. 验证结果 → 确认成功/失败
8. 记录数据库 → 更新提交状态
```

### 预检查清单

- [ ] 站点是否能访问？（避免 404/500）
- [ ] 是否需要登录？
- [ ] 是否有验证码？
- [ ] 是否需要上传文件？

---

## 五、博客评论策略

**优势**：无验证码、无登录、有 URL 字段

### 适用站点特征

- WordPress 博客（评论区有 URL 字段）
- 影视/娱乐/技术类博客
- 审核相对宽松

### 评论模板

```
Great article! I really enjoyed your analysis of [主题].
The points about [具体内容] were particularly insightful.
By the way, for anyone interested in [相关话题], 
check out this free tool: [URL]
```

### 注意事项

- 评论内容要与文章相关
- 不要太明显是广告
- 可能需要等待审核

---

## 六、障碍处理

| 障碍 | 说明 | 解决方案 |
|------|------|---------|
| 🛡️ Turnstile | Cloudflare 人机验证 | 需主人点击验证 |
| 🤖 reCAPTCHA | Google 人机验证 | 需主人点击验证 |
| 🔐 需登录 | 需注册账号 | 主人提供账号 |
| 📎 需上传 | 必须上传图片 | 准备 Logo 文件 |
| ❌ 服务器错误 | 后端配置问题 | 无法解决，跳过 |

---

## 七、项目模板

每个网站项目在 `templates/` 目录下有一个模板文件：

```markdown
# 项目名 提交模板

## 基本信息

| 项目 | 内容 |
|------|------|
| 网站名称 | ... |
| 网址 | ... |
| 一句话描述 | ... |
| 详细描述 | ... |
| 标签/Tags | ... |
| 类别 | ... |

## 提交用链接

- 首页：...
```

---

## 八、常用命令

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

## 九、成功率统计

| 类型 | 成功率 | 说明 |
|------|-------|------|
| 博客评论 | ~60% | 需找开放评论的博客 |
| 目录提交 | ~20% | 多数有验证码/付费门槛 |
| Profile 页面 | ~10% | 需注册+验证码 |

---

## 十、最佳实践

1. **先测试后批量**：新站点先测试一次，确认可提交再批量
2. **控制频率**：每次提交间隔 1-3 分钟，避免被封
3. **记录详细**：失败要记录原因，方便后续优化
4. **定期清理**：删除失效站点，更新站点状态
5. **优先高质量**：优先提交权重高、相关性强的站点

---

## 附录：CloakBrowser 使用

```python
from cloakbrowser import launch

# 启动浏览器
browser = launch(
    headless=True,           # 无头模式
    proxy="http://127.0.0.1:7890"  # 代理
)

# 打开页面
page = browser.new_page()
page.goto("https://example.com", timeout=30000)

# 截图
page.screenshot(path="screenshot.png")

# 获取内容
content = page.content()
title = page.title()

# 关闭
browser.close()
```

---

**文档版本**: v1.0  
**最后更新**: 2026-05-31
