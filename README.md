# SLB 申论AI批改平台

> AI智能批改 + 好词好句鉴赏 + 薄弱点追踪

## 功能特性

- **AI多维批改**：踩点命中 + 逻辑结构 + 语言规范 + 字数控制 + 卷面整洁
- **官媒好词好句**：人民日报、求是网、新华网精选，支持收藏分类
- **薄弱点追踪**：自动记录遗漏采分点，针对性推荐练习
- **全端覆盖**：Web + Telegram Bot，随时随地学习

## 快速部署

### 1. 克隆仓库
```bash
git clone https://github.com/mkih76/SLB.git
cd SLB
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 初始化数据库
```bash
sqlite3 data/slb.db < data/schema.sql
```

### 4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入配置
```

### 5. 运行
```bash
python src/app.py
# 或生产环境:
gunicorn -w 4 -b 0.0.0.0:8790 src.app:app
```

### 6. Docker 部署
```bash
docker-compose up -d
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Flask + Python |
| 数据库 | SQLite |
| AI批改 | GPT-4o-mini / DeepSeek |
| 前端 | HTML5 + Vanilla JS |
| 机器人 | Telegram Bot |
| 部署 | Docker + Caddy |

## 项目结构

```
SLB/
├── src/                 # 源代码
│   ├── app.py          # Flask入口
│   ├── models/         # 数据模型
│   ├── services/       # 业务逻辑
│   ├── api/            # API路由
│   ├── grader/         # AI批改核心
│   ├── crawler/        # 爬虫模块
│   └── bot/            # Telegram Bot
├── data/               # 数据文件
│   ├── schema.sql     # 建表语句
│   └── slb.db         # SQLite数据库
├── templates/          # 前端模板
├── static/            # 静态资源
└── tests/            # 测试
```

## 界面预览

- 深蓝/藏青主色调（正气、官方风格）
- 金色点缀（权威感）
- 思源黑体（清晰正式）

## License

MIT
