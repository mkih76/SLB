# 学习强国文章抓取方案说明

## 概述

时政热点模块从两个渠道抓取内容：
1. **人民网合作源**（requests 直接抓取）：时评、理论、党建三个板块
2. **学习强国 SPA 页面**（Playwright + Cookies）：习近平重要文章专栏

---

## 一、人民网抓取（简单，无需登录）

文件：`src/services/topic_scraper.py` 中的 `fetch_shiping()` / `fetch_lilun()` / `fetch_dangjian()`

直接用 `requests.get()` 抓取人民网 HTML 页面，通过正则提取 `<p>` 标签中的段落文本。无需认证，无需 JavaScript 渲染。

---

## 二、学习强国抓取（Playwright + Cookies）

### 为什么需要 Playwright

学习强国（xuexi.cn）是一个 SPA（单页应用），文章列表由 JavaScript 动态渲染。普通的 `requests.get()` 只能拿到空壳 HTML，无法获取文章内容。必须用 Playwright 启动真实浏览器来渲染页面。

### 为什么需要 Cookies

学习强国的部分页面需要登录态才能显示完整内容。我们通过导入用户浏览器的 Cookies 来模拟登录状态，无需输入密码。

### Cookies 文件

- **路径**：`D:\新建文件夹\下载\www.xuexi.cn.cookies.json`
- **格式**：Playwright 标准格式的 Cookie 数组
- **字段说明**：
  ```json
  [
    {
      "name": "token",
      "value": "69d8a0bfe3144faabfc7a10fced33eb2",
      "domain": ".xuexi.cn",
      "path": "/",
      "expires": 1779968767.768685,
      "httpOnly": false,
      "secure": false
    }
  ]
  ```
- **关键 Cookie**：
  - `token` — 登录凭证（有时效性，过期需重新导出）
  - `y-open-ua` / `y-open-did` — 设备标识
  - `__UID__` — 用户唯一标识

### 如何更新 Cookies

当 Cookies 过期（通常 token 有效期 12-24 小时），需要重新导出：

1. 在 Chrome 浏览器中登录 `www.xuexi.cn`
2. 安装浏览器插件 **EditThisCookie** 或 **Cookie-Editor**
3. 在学习强国页面上，点击插件图标 → 导出 → 选择 JSON 格式
4. 将导出的内容覆盖保存到 `D:\新建文件夹\下载\www.xuexi.cn.cookies.json`

或者使用 Playwright 自带的 `context.storage_state()` 方法：
```python
# 在已登录的 Playwright 浏览器中保存 cookies
await context.storage_state(path="www.xuexi.cn.cookies.json")
```

### 抓取流程详解

函数入口：`src/services/topic_scraper.py` → `fetch_xuexi_articles()`

```
Step 1: 加载 Cookies
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
    ↓
Step 5: 逐篇打开文章详情页，提取正文
    通过 document.querySelectorAll('p') 获取所有 <p> 标签文本
    ↓
Step 6: 清洗文本（去除页脚、版权信息等）
    ↓
Step 7: 写入数据库 hot_topics 表
    category = 'xuexi'
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
通过正则 `id=(\d+)` 提取文章 ID。

**3. 正文提取策略**

学习强国文章详情页的正文容器没有统一的 class 名称，因此采用 `<p>` 标签提取法：
```javascript
var ps = document.querySelectorAll('p');
var parts = [];
for (var i = 0; i < ps.length; i++) {
    var t = ps[i].innerText.trim();
    if (t.length > 5) parts.push(t);
}
return parts.join('\n\n');
```
如果 `<p>` 标签不足 3 个，则回退到 `document.body.innerText`。

**4. 文本清洗**

去除以下页脚内容：
- `服务电话：12361`
- `中央宣传部宣传舆情研究中心版权所有`
- `Copyright© ...`
- `互联网新闻信息服务许可证...`
- `ICP备案...`
- `字体支持：...`

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

1. 检查 Cookies 是否过期（token 字段）
2. 检查 `D:\新建文件夹\下载\www.xuexi.cn.cookies.json` 文件是否存在
3. 在浏览器中手动访问学习强国，确认登录状态正常

### Q: Playwright 报错 `BrowserType.launch`

需要安装 Playwright 浏览器：
```bash
pip install playwright
playwright install chromium
```

### Q: 文章正文为空

可能是页面加载太慢。在 `fetch_xuexi_articles()` 中增加 `page.wait_for_timeout()` 的等待时间。

### Q: 如何修改抓取时间范围

在 `fetch_xuexi_articles()` 中修改：
```python
CUTOFF = datetime.now() - timedelta(days=180)  # 改为你需要的天数
```

### Q: 如何添加新的学习强国页面

修改 `PAGE_URL` 变量为目标页面地址。注意：
- 页面必须是 `grid-cell` 布局（大多数学习强国栏目页都是）
- 文章卡片必须包含日期信息用于筛选

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
