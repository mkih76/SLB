# 粉笔数据抓取方案

## 概述

SLB 从粉笔教育获取申论真题和备考资料，采用两种抓取策略：

1. **网盘公开资料**（`fenbi_public.py`）— 无需登录，直接下载 PDF
2. **题库真题**（`fenbi_tiku.py`）— 需要粉笔账号，通过 API 获取真题试卷

---

## 一、网盘公开资料（无需登录）

### 发现过程

粉笔网盘 (`www.fenbi.com/fpr/doc-user-v2/dir/xxx`) 是 SPA 页面。通过 Playwright 拦截网络请求，发现底层 API 完全公开：

| 功能 | 端点 | 认证 |
|------|------|------|
| 目录列表 | `GET https://webapi.fenbi.com/doc/api/publs/{dir_id}` | ❌ 不需要 |
| 文件下载 | `GET https://nodestatic.fbstatic.cn/pan/downloads/{cospath}` | ❌ 不需要 |

### 使用方法

```python
from src.crawler.fenbi_public import FenbiPublicScraper

scraper = FenbiPublicScraper(output_dir="./data/fenbi_shenlun")

# 下载单个目录
scraper.download_dir(28695, "2024国考申论密卷")

# 下载所有预设申论目录
stats = scraper.download_all()

# 扫描新目录
found = scraper.scan_range(30000, 30100)
```

### CLI

```bash
# 下载全部预设资料
python src/crawler/fenbi_public.py

# 扫描目录 ID 范围，发现新的分享
python src/crawler/fenbi_public.py scan 40000 40100
```

### 已知目录 ID

| ID | 内容 |
|----|------|
| 28695 | 2024国考申论密卷（行政执法/副省级/地市级，各5套） |
| 28704 | 2024浙江省考申论密卷（A/B/C三类，各5套） |
| 40326 | 2025国考申论解析 |
| 40328 | 2025省考申论解析 |
| 22202 | 历年国考真题（2019-2023 zip） |
| 35591 | 三色笔记（行测/申论/公基） |
| 25001 | 申论基础（思维导图/金句/模板/范文） |
| 25030 | 申论资料包（规范词/公文格式/范文/金词） |
| 32741 | 2025国联考申论热点范文 |
| 32267 | 申论高分必背素材 |
| 32266 | 申论常用名言1000句 |
| 28690 | 申论金词金句热点素材 |
| 36828 | 粉笔辅导员资料合集 |

> 目录 ID 是递增的，可以通过 `scan_range()` 扫描发现新目录。

---

## 二、题库真题（需要登录）

### 技术原理

粉笔题库 (`tiku.fenbi.com`) 的 API 流程：

```
登录 → 获取分类 → 获取试卷列表 → 创建练习 → 下载 PDF
```

| 步骤 | API | 方法 |
|------|-----|------|
| 登录 | `POST login.fenbi.com/api/users/loginV2` | RSA 加密密码 |
| 分类列表 | `GET tiku.fenbi.com/api/{type}/subLabels` | Cookie 认证 |
| 试卷列表 | `GET tiku.fenbi.com/api/{type}/papers?labelId=X` | Cookie 认证 |
| 创建练习 | `POST tiku.fenbi.com/api/{type}/exercises` | Cookie 认证 |
| 下载 PDF | `GET urlimg.fenbi.com/api/pdf/tiku/{type}/exercise/{id}` | Cookie 认证 |

其中 `{type}` 为 `shenlun`（申论）或 `xingce`（行测）。

### 密码加密

粉笔使用 RSA 公钥加密密码，公钥硬编码在前端 `encrypt.js` 中。加密逻辑用 Node.js 执行。

### 使用方法

```python
from src.crawler.fenbi_tiku import FenbiTikuScraper

scraper = FenbiTikuScraper(
    phone="13800138000",
    password="your_password",
    output_dir="./data/fenbi_zhenti"
)

# 登录
scraper.login()

# 下载全部申论真题
stats = scraper.download_papers("shenlun")

# 只下载指定省份
stats = scraper.download_papers("shenlun", provinces=["江西", "重庆"])
```

### CLI

```bash
# 下载全部申论真题
python src/crawler/fenbi_tiku.py 13800138000 mypassword shenlun

# 只下载指定省份
python src/crawler/fenbi_tiku.py 13800138000 mypassword shenlun 江西,重庆

# 下载行测真题
python src/crawler/fenbi_tiku.py 13800138000 mypassword xingce
```

---

## 三、数据存储

```
data/
├── fenbi_shenlun/          # 网盘公开资料
│   ├── 2024国考申论密卷/
│   │   ├── 行政执法/
│   │   ├── 副省级/
│   │   └── 地市级/
│   ├── 2024浙江省考申论密卷/
│   ├── 三色笔记/
│   ├── 申论基础/
│   └── ...
└── fenbi_zhenti/            # 题库真题（需登录下载）
    ├── shenlun/
    │   ├── 江西/
    │   ├── 重庆/
    │   └── ...
    └── xingce/
```

---

## 四、注意事项

1. **礼貌抓取**：所有请求间有 0.2-0.5s 间隔，避免给服务器造成压力
2. **Cookie 时效**：题库登录 Cookie 会过期，过期后需重新登录
3. **RSA 公钥**：如果粉笔更换公钥，需要从前端 `encrypt.js` 重新提取
4. **目录发现**：网盘目录 ID 持续递增，定期扫描可发现新资料
5. **仅供学习**：抓取内容仅供个人学习使用，请勿用于商业用途
