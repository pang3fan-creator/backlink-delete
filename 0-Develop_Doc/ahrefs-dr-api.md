# Ahrefs 免费 DR 查询 API

**发现日期**：2026-06-10

## 接口地址

```
https://api.ahrefs.com/v3/public/domain-rating-free?target=<域名>
```

## 特点

- ✅ **免费公开**，无需认证
- ✅ **无速率限制**（实测并发 10 路，478 站 44 秒跑完）
- ✅ 返回简洁，只有一个 DR 值

## 返回格式

```json
{
  "domain_rating": {
    "domain_rating": 50.0
  }
}
```

## 使用示例

```bash
# 单次查询
curl -s "https://api.ahrefs.com/v3/public/domain-rating-free?target=google.com"

# 返回
{"domain_rating":{"domain_rating":100.0}}
```

## 批量更新数据库

```python
import json, sqlite3, concurrent.futures, subprocess
from urllib.parse import urlparse

DB_PATH = "/root/projects/own/0-backlink-submit/backlinks.db"

conn = sqlite3.connect(DB_PATH)
sites = conn.execute("SELECT id, site_url FROM sites WHERE weight IS NULL").fetchall()
conn.close()

def extract_domain(url):
    netloc = urlparse(url).netloc
    return netloc.lstrip("www.") if netloc else None

def fetch_dr(site_id, url):
    domain = extract_domain(url)
    if not domain:
        return (site_id, None)
    try:
        r = subprocess.run(
            ['curl', '-s', '--max-time', '8',
             f'https://api.ahrefs.com/v3/public/domain-rating-free?target={domain}'],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(r.stdout)
        dr = data.get('domain_rating', {}).get('domain_rating', None)
        return (site_id, float(dr) if dr else None)
    except:
        return (site_id, None)

# 并发查询
results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(fetch_dr, s[0], s[1]): s for s in sites}
    for f in concurrent.futures.as_completed(futures):
        results.append(f.result())

# 写入数据库
conn = sqlite3.connect(DB_PATH)
for site_id, dr in results:
    if dr:
        conn.execute("UPDATE sites SET weight = ? WHERE id = ?", (int(round(dr)), site_id))
conn.commit()
conn.close()
```

## 注意事项

1. **DR 可被操纵** — 通过垃圾外链可以刷高 DR，但大部分网站的 DR 值还是有参考价值
2. **没有 RD/RP 接口** — Ahrefs 没有公开外链域名数（RD）和外链页面数（RP）的免费接口
3. **域名格式** — 去掉 `www.` 前缀，使用裸域名查询

## 实测数据（2026-06-10）

- 站点数：478
- 耗时：44 秒
- 成功率：96%（460/478）
- DR 分布：平均 45.2，最高 97

## 参考

- Ahrefs DR 计算漏洞：https://new.web.cafe/tutorial/detail/z63ok6t2u6
