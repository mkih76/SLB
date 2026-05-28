# 学习强国文章抓取方案说明

## 概述

时政热点模块从两个渠道抓取内容：
1. **人民网合作源**（requests 直接抓取）：时评、理论、党建三个板块
2. **学习强国 SPA 页面**（Playwright）：习近平重要文章专栏

---

## 一、人民网抓取（简单，无需登录）

文件：`src/services/topic_scraper.py` 中的 `fetch_shiping()` / `fetch_lilun()` / `fetch_dangjian()`

直接用 `requests.get()` 抓取人民网 HTML 页面，通过正则提取 `<p>` 标签中的段落文本。无需认证，无需 JavaScript 渲染。

---

## 二、学习强国抓取（Playwright）

### 技术调研结论

经过完整测试，学习强国的技术特性如下：

| 特性 | 结论 | 说明 |
|------|------|------|
| SPA 架构 | 是 | 文章列表由 JS 动态渲染，`requests` 只能拿到空壳 HTML |
| 旧版 JSON API | 已废弃 | `/lgdata/*.json`、`/datasource/*.json` 全部返回 404/302 |
| 新版 API (`pc-api.xuexi.cn`) | 需认证 | `/open/api/auth/check` 可访问但 `data:null` |
| 文章详情页 | **公开** | 不需要 cookies 即可读取完整正文（实测 9910 字） |
| 文章列表页 | 需登录 | 无 cookies 时 `grid-cell` 数量为 0 |
| Cookies 自动更新 | 不可行 | 登录需 QR 码扫码，无法自动化 |
| 搜索引擎索引 | 有限 | VPS IP 被 Google/Bing/DDG 限流，不稳定 |
| Jina Reader 首页 | 可获取标题 | 能拿到文章标题文本，但无法获取文章链接（SPA） |

**核心发现：文章详情页是公开的，正文抓取不需要 cookies。cookies 仅用于从列表页发现文章 URL。**

### 两层架构

```
发现层（获取文章 URL）
├─ 方式 A: cookies + 列表页 grid-cell 点击（有 cookies 时）
└─ 方式 B: URL 缓存文件 ~/.hermes/xuexi_urls.json（无 cookies 时）
         └─ 由外部 cron/手动写入

抓取层（读取正文）← 始终不需要 cookies
└─ Playwright 打开详情页 → [class*=title] 提取标题 → <p> 标签提取正文
```

### Cookies 文件

- **路径优先级**：`~/.hermes/xuexi_cookies.json` > `D:\新建文件夹\下载\www.xuexi.cn.cookies.json`
- **格式**：Playwright 标准格式的 Cookie 数组
- **关键 Cookie**：
  - `token` — 登录凭证（有效期 12-24 小时，过期需重新导出）
  - `y-open-ua` / `y-open-did` — 设备标识（PC 客户端 TorchApp/2.19.0）
  - `__UID__` — 用户唯一标识（有效期 1 年）

### 如何更新 Cookies

当 Cookies 过期（通常 token 有效期 12-24 小时），需要重新导出：

1. 在 Chrome 浏览器中登录 `www.xuexi.cn`
2. 安装浏览器插件 **EditThisCookie** 或 **Cookie-Editor**
3. 在学习强国页面上，点击插件图标 → 导出 → 选择 JSON 格式
4. 将导出的内容覆盖保存到 cookies 文件

或者使用 Playwright 自带的 `context.storage_state()` 方法：
```python
await context.storage_state(path="www.xuexi.cn.cookies.json")
```

**注意：Cookies 不可自动更新。** 学习强国登录需要 QR 码扫码 + 手机验证，无法程序化完成。

### 方式 A：Cookies + 列表页发现

```
Step 1: 加载 Cookies → context.add_cookies()
    ↓
Step 2: 打开文章列表页
    https://www.xuexi.cn/6db80fbc0859e5c06b81fd5d6d618749/
    9a3668c13f6e303932b5e0e100fc248b.html
    ↓
Step 3: 从 DOM 中找到带日期的 grid-cell 元素
    筛选最近 6 个月的文章
    ↓
Step 4: 逐个点击 grid-cell，捕获跳转 URL
    文章链接格式：https://www.xuexi.cn/lgpage/detail/index.html?id=<文章ID>
```

### 方式 B：URL 缓存文件

当 cookies 不可用或过期时，从 `~/.hermes/xuexi_urls.json` 读取文章 URL。

**文件格式：**
```json
[
  {"id": "16005681563345065647", "url": "https://www.xuexi.cn/lgpage/detail/index.html?id=...", "date": "2026-05-15"},
  {"id": "9667311837782231390", "url": "https://www.xuexi.cn/lgpage/detail/index.html?id=...", "date": "2026-05-15"}
]
```

**填充方式：**
- Hermes cron 定期搜索 `site:xuexi.cn/lgpage/detail` 写入（已配置但暂停）
- 手动从搜索引擎收集 URL 写入
- 从其他系统/API 推送

### 正文抓取（不需要 cookies）

```
Step 1: Playwright 打开文章详情页
    ↓
Step 2: 标题提取
    document.querySelector('[class*=title]')  ← 优先
    || document.querySelector('.article-title')  ← 回退
    || document.querySelector('h1')  ← 兜底
    ↓
Step 3: 正文提取
    document.querySelectorAll('p') → 过滤 >5 字的段落 → join('\n\n')
    如果 <p> 不足 3 个 → 回退到 document.body.innerText
    ↓
Step 4: 文本清洗
    去除页脚: 服务电话、版权声明、ICP备案等
    ↓
Step 5: 写入数据库 hot_topics 表
```

### 关键技术细节

**1. 文章列表页的链接机制**

学习强国的文章列表不是标准的 `<a>` 标签。文章卡片是 `div.grid-cell` 元素，点击后由 JavaScript 触发页面跳转。因此：
- 不能通过 `href` 属性获取链接
- 必须用 Playwright 模拟点击，然后从新页面的 URL 中提取文章 ID

**2. 文章 ID 提取**

点击后跳转到：
```
https://www.xuexi.cn/lgpage/detail/index.html?id=16005681563345065647&item_id=16005681563345065647
```
通过正则 `id=(\d+)` 提取文章 ID（通常是 19-20 位数字）。

**3. 标题选择器**

学习强国文章详情页的标题元素没有统一的 `article-title` class。实际 DOM 中标题元素的 class 名称包含 `title` 字样但不固定，因此使用 `[class*=title]` CSS 选择器匹配。

**4. 正文提取策略**

正文容器没有统一的 class 名称，采用 `<p>` 标签提取法：
```javascript
var ps = document.querySelectorAll('p');
var parts = [];
for (var i = 0; i < ps.length; i++) {
    var t = ps[i].innerText.trim();
    if (t.length > 5) parts.push(t);
}
return parts.join('\n\n');
```

**5. 文本清洗**

去除以下页脚内容：
- `服务电话：12361`
- `中央宣传部宣传舆情研究中心版权所有`
- `Copyright© ...`
- `互联网新闻信息服务许可证...`
- `ICP备案...`

### 数据库字段

```sql
INSERT INTO hot_topics (
    title,           -- 文章标题（如 "习近平：坚定不移推进高水平对外开放"）
    summary,         -- 原文前 200 字
    category,        -- 'xuexi'（学习强国专属分类）
    keywords,        -- '[]'（暂不使用）
    source_url,      -- 学习强国原文链接
    original_text,   -- 完整原文（通常 2000-10000 字）
    week_label,      -- 发布年月（如 "2026-05"）
    status           -- 'published'
) VALUES (...);
```

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `GET /api/topics?category=xuexi` | GET | 获取学习强国文章列表 |
| `GET /api/topics/<id>` | GET | 获取文章详情（含原文） |
| `POST /api/topics/scrape-xuexi` | POST | 触发抓取（需管理员权限） |
| `GET /topics/<id>` | GET | 文章详情页面（浏览器访问） |

### 前端页面

- **列表页** `/topics` — 筛选器中有"学习强国"按钮
- **详情页** `/topics/<id>` — 独立页面（非弹窗），显示完整原文，有"查看原文 ↗"链接

---

## 三、常见问题排查

### Q: 抓取到 0 篇文章

**有 cookies 时：**
1. 检查 Cookies 是否过期（token 字段有效期 12-24 小时）
2. 检查 cookies 文件是否存在（优先级：`~/.hermes/xuexi_cookies.json` > Windows 路径）
3. 在浏览器中手动访问学习强国，确认登录状态正常

**无 cookies 时：**
1. 检查 `~/.hermes/xuexi_urls.json` 是否存在且非空
2. 手动写入几个已知文章 URL 测试
3. 启用 Hermes cron 定期搜索新文章

### Q: Playwright 报错 `BrowserType.launch`

需要安装 Playwright 浏览器：
```bash
pip install playwright
playwright install chromium
playwright install-deps chromium  # Linux 需要安装系统依赖
```

### Q: 文章正文为空

可能是页面加载太慢。在 `fetch_xuexi_articles()` 中增加 `page.wait_for_timeout()` 的等待时间。

### Q: 如何修改抓取时间范围

在 `fetch_xuexi_articles()` 中修改：
```python
CUTOFF = datetime.now() - timedelta(days=180)  # 改为你需要的天数
```

### Q: 如何手动添加文章 URL

编辑 `~/.hermes/xuexi_urls.json`：
```json
[
  {"id": "文章ID", "url": "https://www.xuexi.cn/lgpage/detail/index.html?id=文章ID&item_id=文章ID", "date": "2026-05-27"}
]
```

### Q: Cookies 过期后怎么办

Cookies 无法自动更新（登录需 QR 码扫码）。两个选择：
1. 重新从浏览器导出 cookies
2. 不管 cookies，依赖 URL 缓存文件（手动或 cron 填充）

---

## 四、文件清单

| 文件 | 说明 |
|------|------|
| `src/services/topic_scraper.py` | 所有抓取逻辑（人民网 + 学习强国） |
| `src/services/topic_service.py` | 热点数据服务（含 xuexi 分类） |
| `src/api/topic.py` | API 端点（含 scrape-xuexi） |
| `src/app.py` | 页面路由（含 /topics/<id>） |
| `templates/topics.html` | 热点列表页 |
| `templates/topic_detail.html` | 文章详情页 |
| `docs/xuexi_scraper.md` | 本文档 |
