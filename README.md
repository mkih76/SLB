# SLB 申论帮

> AI 驱动的公务员申论备考平台 — 智能批改 · 好词好句 · 薄弱点追踪 · 全端覆盖

## 核心功能

| 模块 | 说明 |
|------|------|
| **AI 多维批改** | 五维度评分：踩点命中、逻辑结构、语言规范、字数控制、卷面整洁 |
| **真题卷库** | 393 套真题，覆盖国考 + 31 省省考 + 联考（2011-2026），共 271 万字 |
| **题型训练** | 归纳概括、综合分析、提出对策、贯彻执行、申论大作文，分类专项练习 |
| **能力诊断** | 雷达图五维度分析，自动识别薄弱点，推荐针对性练习 |
| **好词好句** | 人民日报、求是网、新华网精选素材，支持收藏分类 |
| **备考计划** | 个性化学习计划，进度追踪 |
| **时政热点** | 实时热点整理，关联申论考点 |
| **粉笔资料** | 一键下载粉笔教育公开申论资料（约 290MB） |
| **管理后台** | 用户管理、试卷管理、数据统计、LLM 配置 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3.0 + Python 3.11 |
| 数据库 | SQLite（零配置，单文件部署） |
| AI 引擎 | OpenAI 兼容 API（DeepSeek / GPT-4o-mini 等） |
| 前端 | HTML5 + Vanilla JS + Chart.js + 设计系统（Stripe 风格） |
| 部署 | Docker + Caddy 反向代理 |
| 可选 | Telegram Bot、Redis 缓存 |

## 快速部署

### 方式一：Docker（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/mkih76/SLB.git && cd SLB

# 2. 一键部署（自动安装 Docker、生成 .env、构建启动）
bash deploy.sh

# 3. 编辑 .env 填入 LLM API Key
nano .env  # 必填：LLM_API_KEY

# 4. 重启服务
docker compose restart
```

部署完成后：
- 访问地址：`http://<服务器IP>:8790`
- 管理后台：`http://<服务器IP>:8790/admin`
- 默认管理员：`admin` / `admin123456`（**请立即修改密码**）

### 方式二：手动部署

```bash
# 1. 克隆仓库
git clone https://github.com/mkih76/SLB.git && cd SLB

# 2. 安装依赖
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
nano .env  # 填入 LLM_API_KEY 等配置

# 4. 初始化数据库
sqlite3 data/slb.db < data/schema.sql

# 5. 导入真题数据（可选，393 套）
sqlite3 data/slb.db < data/seed_papers.sql
sqlite3 data/slb.db < data/seed_phrases.sql
sqlite3 data/slb.db < data/seed_topics.sql

# 6. 启动
python src/app.py                    # 开发模式
gunicorn -w 4 -b 0.0.0.0:8790 src.app:app  # 生产模式
```

### Caddy 反向代理（HTTPS）

```bash
# /etc/caddy/Caddyfile
slb.19990419.top {
    reverse_proxy localhost:8790
}
```

```bash
systemctl reload caddy
```

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `SECRET_KEY` | ✅ | — | Flask 密钥（`openssl rand -hex 32` 生成） |
| `JWT_SECRET` | ✅ | — | JWT 签名密钥 |
| `LLM_API_KEY` | ✅ | — | LLM API 密钥 |
| `LLM_BASE_URL` | — | `https://api.deepseek.com/v1` | LLM API 地址 |
| `LLM_MODEL` | — | `deepseek-chat` | 模型名称 |
| `DATABASE_PATH` | — | `data/slb.db` | 数据库路径 |
| `TG_BOT_TOKEN` | — | — | Telegram Bot Token（可选） |
| `REDIS_HOST` | — | `localhost` | Redis 地址（可选，用于缓存） |
| `PORT` | — | `8790` | 服务端口 |

> **安全提示**：生产环境 `SECRET_KEY` 和 `JWT_SECRET` 必须使用随机生成的强密钥，禁止使用默认值。

## 项目结构

```
SLB/
├── src/                        # 后端源码
│   ├── app.py                  # Flask 入口 + 路由注册
│   ├── config.py               # 环境变量配置 + 动态 LLM 配置
│   ├── api/                    # API 蓝图（RESTful）
│   │   ├── auth.py             # 认证（注册/登录/签到）
│   │   ├── papers.py           # 试卷查询
│   │   ├── submissions.py      # 提交批改
│   │   ├── phrases.py          # 好词好句
│   │   ├── weak.py             # 薄弱点
│   │   ├── drill.py            # 题型训练
│   │   ├── diagnosis.py        # 能力诊断
│   │   ├── simulation.py       # 模拟考试
│   │   ├── plan.py             # 备考计划
│   │   ├── topic.py            # 时政热点
│   │   ├── community.py        # 社区
│   │   └── admin.py            # 管理后台 API
│   ├── services/               # 业务逻辑层
│   └── crawler/                # 爬虫模块
│       ├── fenbi_public.py     # 粉笔公开资料下载
│       └── fenbi_tiku.py       # 粉笔题库真题（需账号）
├── templates/                  # 前端模板（29 个页面）
│   ├── base.html               # 基础布局（导航栏 + 移动端菜单 + 返回顶部）
│   ├── index.html              # 首页
│   ├── papers.html             # 卷库
│   ├── exam.html               # 答题页
│   ├── result.html             # 批改结果
│   ├── diagnosis.html          # 能力诊断
│   ├── profile.html            # 个人中心（图表 + 学习数据）
│   ├── admin/                  # 管理后台（8 个页面）
│   └── ...
├── static/                     # 静态资源
│   ├── css/
│   │   ├── variables.css       # 设计令牌（色彩/字体/间距/阴影）
│   │   ├── interactions.css    # 交互动效（滚动进场/toast/焦点环）
│   │   ├── components.css      # 组件库（21 个组件）
│   │   ├── main.css            # 基础样式 + 布局
│   │   └── admin.css           # 管理后台样式
│   └── js/
│       ├── components.js       # 组件交互 + Chart.js 封装
│       ├── app.js              # 全局逻辑（认证/Toast/API）
│       └── exam.js             # 答题页逻辑
├── data/
│   ├── schema.sql              # 建表语句
│   ├── seed_papers.sql         # 试卷种子数据
│   ├── seed_phrases.sql        # 好词好句种子数据
│   ├── seed_topics.sql         # 时政热点种子数据
│   └── shenlun_zhenti/         # 393 套申论真题原文（Markdown）
├── scripts/                    # 工具脚本
│   ├── fenbi_download.py       # 粉笔资料一键下载
│   ├── scrape_shenlunhome.com  # 申论之家真题爬虫
│   └── auto_update.py          # 自动更新
├── DESIGN.md                   # 设计系统规范（Stripe 风格）
├── AGENTS.md                   # AI 编码代理构建指引
├── Dockerfile                  # Docker 镜像定义
├── docker-compose.yml          # Docker Compose 编排
├── deploy.sh                   # 一键部署脚本
└── requirements.txt            # Python 依赖
```

## 前端组件库

项目内置 21 个 UI 组件，遵循 Stripe 风格设计系统（详见 `DESIGN.md` + `AGENTS.md`）：

| 组件 | 说明 |
|------|------|
| 骨架屏 | shimmer 加载占位 |
| AI 批改进度条 | 4 段式进度 + 状态文字 |
| Toast 通知 | 右上角滑入，4 种类型 |
| 移动端菜单 | 汉堡按钮 → X 变形 |
| Tab 页签 | 下划线指示器 |
| 下拉菜单 | 淡入弹出，点击外部关闭 |
| 搜索框 | 自动补全 + 高亮匹配 |
| Tooltip | 4 方向 + 箭头 |
| 手风琴 | 展开折叠动画 |
| 面包屑 | 链接 + 分隔符 |
| 返回顶部 | 滚动触发显示 |
| Checkbox / Radio / Switch | 自定义样式 + 动画 |
| 得分环 | SVG 环形 + countUp 动画 |
| 进度条 | 光泽流动动画 |
| 头像 | 4 尺寸 + 头像组 |
| 评分星级 | 金色填充 |
| Chart.js 图表 | 雷达图 / 柱状图 / 折线图 / 环形图 |
| 时间线 | 竖线 + 状态圆点 |
| 个人中心 | 5 面板（概览/记录/薄弱/收藏/设置） |

**使用示例**：

```js
// Toast 通知
SLBToast.success('提交成功');
SLBToast.error('网络错误', '请重试');

// AI 批改进度条
SLBGradingProgress.start();
SLBGradingProgress.nextStep(0);  // 踩点分析
SLBGradingProgress.nextStep(1);  // 逻辑评估
SLBGradingProgress.finish();

// Chart.js 图表
SLBCharts.radar('canvas-id', {
  labels: ['踩点命中', '逻辑结构', '语言规范', '字数控制', '卷面整洁'],
  data: [80, 65, 72, 90, 60]
});
```

## 数据规模

| 数据集 | 数量 | 说明 |
|--------|------|------|
| 申论真题 | 393 套 | 国考 + 31 省 + 联考，2011-2026 年 |
| 覆盖地区 | 34 个 | 国考 + 23 省 + 5 自治区 + 4 直辖市 + 联考 |
| 总字数 | 271 万字 | Markdown 格式，含题目 + 材料 + 参考答案 |
| 数据库 | SQLite | 零配置，单文件，支持 Docker 持久化卷 |

## 粉笔数据集成

SLB 从粉笔教育获取申论真题和备考资料。详见 [docs/fenbi_scraper.md](docs/fenbi_scraper.md)

```bash
# 一键下载全部公开申论资料（无需登录，约 290MB）
python scripts/fenbi_download.py

# 下载题库真题（需粉笔账号）
python scripts/fenbi_download.py --phone 13800138000 --password xxx

# 扫描发现新目录
python scripts/fenbi_download.py --scan 40000 40100
```

## API 接口

所有 API 以 `/api/` 为前缀，返回 JSON。

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /api/auth/register` | 注册 |
| | `POST /api/auth/login` | 登录 |
| | `GET /api/auth/me` | 当前用户信息 |
| | `POST /api/auth/signin` | 签到 |
| 试卷 | `GET /api/papers` | 试卷列表（筛选/分页） |
| | `GET /api/papers/<pid>` | 试卷详情 |
| 批改 | `POST /api/submissions` | 提交答案 |
| | `GET /api/submissions/<sid>` | 查看批改结果 |
| | `GET /api/submissions/history` | 批改历史 |
| 好词好句 | `GET /api/phrases` | 好词列表 |
| | `POST /api/phrases/<id>/favorite` | 收藏 |
| 薄弱点 | `GET /api/weak` | 薄弱点列表 |
| | `GET /api/weak/stats` | 薄弱点统计 |
| 管理 | `GET /api/admin/dashboard` | 仪表盘数据 |
| | `GET /api/admin/users` | 用户管理 |
| | `GET /api/admin/papers` | 试卷管理 |
| | `GET /api/admin/settings` | 系统设置 |

## 设计系统

项目采用 Stripe 风格设计语言（详见 [DESIGN.md](DESIGN.md)）：

- **主色**：深海军蓝 `#1c1e54` + 靛蓝 `#533afd`
- **点缀色**：金色 `#9b6829` + 米金 `#f5e9d4`
- **字体**：SF Pro Display / Inter，轻字重 300
- **按钮**：药丸形（24px 圆角）
- **卡片**：无阴影，纯边框
- **动效**：安静的专业感 — 用户感知到流畅，但说不出为什么

## License

MIT
