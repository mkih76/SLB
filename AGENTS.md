# AGENTS.md — SLB 申论AI批改平台构建指引

> 给 Claude Code / Codex 等 AI 编码代理使用。
> 本文件定义完整项目结构、代码规范和构建顺序。

---

## 一、项目概述

- **项目名**：SLB（申论帮，ShenLunBen）
- **仓库**：https://github.com/mkih76/SLB
- **核心功能**：粉笔批量抓卷 → 数据库存储 → 用户提交答案 → AI多维度批改 → 好词好句鉴赏
- **目标用户**：备考公务员/事业单位考生
- **技术栈**：Python(Flask) + SQLite + LLM API + Bootstrap/Tailwind + Telegram Bot
- **部署环境**：VPS + Docker + Caddy（与 gaokao-number 共用基础设施）

---

## 二、UI设计规范（正气、官方风格）

### 2.1 色彩体系
| 用途 | 色值 | 说明 |
|------|------|------|
| 主色 | `#1A3A6B` | 藏青/深蓝，正气官方感 |
| 主色亮 | `#2B5BA8` | 悬停/选中态 |
| 辅色/点缀 | `#C9A84C` | 金色，权威感 |
| 背景 | `#F5F7FA` | 浅灰蓝 |
| 卡片背景 | `#FFFFFF` | 纯白 |
| 正文文字 | `#1F2937` | 深灰 |
| 次要文字 | `#6B7280` | 灰色说明 |
| 成功色 | `#059669` | 绿色（得分高） |
| 警告色 | `#D97706` | 橙色 |
| 错误色 | `#DC2626` | 红色（低分） |

### 2.2 字体规范
- 标题：思源黑体 CN Bold，22-28px
- 正文：思源黑体 CN Regular，14-16px
- 数字/代码：JetBrains Mono，Roboto Mono

### 2.3 组件规范
- 卡片：圆角8px，白色背景，阴影`0 1px 3px rgba(0,0,0,0.1)`
- 按钮：圆角6px，主色背景，悬停微变深
- 输入框：1px #D1D5DB边框，聚焦时主色边框
- 表格：斑马纹，行悬停高亮

---

## 三、数据库Schema

### 3.1 完整建表顺序

```sql
-- 用户表
CREATE TABLE users (
    uid           TEXT PRIMARY KEY,          -- UUID
    username      TEXT UNIQUE NOT NULL,      -- 登录用户名
    password_hash TEXT NOT NULL,              -- bcrypt 哈希
    nickname      TEXT,                      -- 显示昵称
    role          TEXT DEFAULT 'user',       -- user / admin / vip
    vip_expire    DATETIME,                  -- VIP过期时间
    created_at    DATETIME DEFAULT NOW,
    last_login    DATETIME,
    status        TEXT DEFAULT 'active',     -- active / banned
    settings      TEXT DEFAULT '{}'          -- JSON
);

-- 会话表
CREATE TABLE sessions (
    sid       TEXT PRIMARY KEY,
    uid       TEXT NOT NULL,
    token     TEXT UNIQUE NOT NULL,
    ip        TEXT,
    created_at DATETIME DEFAULT NOW,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- 试卷表
CREATE TABLE papers (
    pid           TEXT PRIMARY KEY,          -- fb_2024gwy_sl_001
    source        TEXT NOT NULL,
    exam_type     TEXT NOT NULL,             -- 国考 / 省考 / 事业单位
    year          INT NOT NULL,
    season        TEXT,
    province      TEXT,
    title         TEXT NOT NULL,
    material      TEXT NOT NULL,             -- JSON数组（分段材料）
    questions     TEXT NOT NULL,            -- JSON数组（题目+答案要点）
    answer_keys   TEXT NOT NULL,            -- JSON（标准答案）
    difficulty    INT DEFAULT 3,
    heat          INT DEFAULT 0,
    tag           TEXT DEFAULT '[]',
    source_url    TEXT,
    status        TEXT DEFAULT 'published',
    created_at    DATETIME DEFAULT NOW,
    crawled_at    DATETIME
);

-- 题目内嵌JSON结构示例
-- questions字段结构：
-- [
--   {
--     "qid": "q1",
--     "type": "归纳概括",
--     "stem": "根据给定资料，概括...",
--     "score_max": 20,
--     "word_limit": "150-200字",
--     "key_points": [
--       {"point": "完善基础设施建设", "score": 4, "alias": ["修建道路", "基础设施升级"]},
--       {"point": "发展特色产业", "score": 5, "alias": ["产业多元化"]},
--       {"point": "引进专业技术人才", "score": 4, "alias": ["人才引进"]}
--     ],
--     "model_answer": "标准答案全文...",
--     "scoring_rule": "按点给分，少一点扣X分",
--     "common_mistakes": ["要点遗漏", "过度展开"]
--   }
-- ]

-- 提交记录表
CREATE TABLE submissions (
    sid           TEXT PRIMARY KEY,
    uid           TEXT NOT NULL,
    pid           TEXT NOT NULL,
    qid           TEXT NOT NULL,
    user_answer   TEXT NOT NULL,
    score         REAL,
    dimension_scores TEXT,
    ai_feedback   TEXT,
    hit_points    TEXT DEFAULT '[]',
    missing_points TEXT DEFAULT '[]',
    improving_suggestions TEXT,
    graded_at     DATETIME,
    is_reviewed   INT DEFAULT 0,
    created_at    DATETIME DEFAULT NOW,
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (pid) REFERENCES papers(pid)
);

-- 薄弱点表
CREATE TABLE weak_points (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uid           TEXT NOT NULL,
    pid           TEXT,
    qid           TEXT,
    missing_key   TEXT NOT NULL,
    topic_tag     TEXT,
    times_missed  INT DEFAULT 1,
    review_count  INT DEFAULT 0,
    last_reviewed DATETIME,
    created_at    DATETIME DEFAULT NOW,
    UNIQUE(uid, missing_key)
);

-- 好词好句表
CREATE TABLE good_phrases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase        TEXT NOT NULL,
    translation   TEXT,
    usage         TEXT,
    source        TEXT NOT NULL,
    source_url    TEXT,
    source_date   DATE,
    tag           TEXT DEFAULT '[]',
    heat          INT DEFAULT 0,
    status        TEXT DEFAULT 'pending',
    approved_by   TEXT,
    created_at    DATETIME DEFAULT NOW
);

-- 好词收藏表
CREATE TABLE user_favorites (
    uid           TEXT NOT NULL,
    phrase_id     INTEGER NOT NULL,
    note          TEXT,
    created_at    DATETIME DEFAULT NOW,
    PRIMARY KEY (uid, phrase_id)
);

-- 学习记录表
CREATE TABLE learning_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uid           TEXT NOT NULL,
    action        TEXT NOT NULL,
    target_id     TEXT NOT NULL,
    score         REAL,
    created_at    DATETIME DEFAULT NOW
);

-- 管理员日志表
CREATE TABLE admin_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_uid     TEXT NOT NULL,
    action        TEXT NOT NULL,
    target_type   TEXT,
    target_id     TEXT,
    detail        TEXT,
    created_at    DATETIME DEFAULT NOW
);
```

---

## 四、API 接口设计

### 4.1 认证 `/api/auth`
```
POST /api/auth/register
  Body: {username, password, nickname}
  → {token, user: {uid, nickname, role}}

POST /api/auth/login
  Body: {username, password}
  → {token, user: {uid, nickname, role}}

POST /api/auth/logout
  Header: Authorization: Bearer <token>
  → {message: "ok"}

GET /api/auth/me
  Header: Authorization: Bearer <token>
  → {uid, username, nickname, role, vip_expire}
```

### 4.2 试卷 `/api/papers`
```
GET /api/papers
  Query: ?exam_type=国考&year=2024&type=归纳概括&page=1&limit=20
  → {papers: [...], total: 186, page: 1, pages: 10}

GET /api/papers/<pid>
  → {paper with full questions and materials}

GET /api/papers/<pid>/question/<qid>
  → {qid, type, stem, score_max, word_limit, material_segments}
```

### 4.3 提交批改 `/api/submissions`
```
POST /api/submissions
  Header: Authorization: Bearer <token>
  Body: {pid, qid, user_answer}
  → {sid, status: "grading"}

GET /api/submissions/<sid>
  → {score, dimension_scores, ai_feedback, hit_points, missing_points}

GET /api/submissions/history
  Query: ?page=1&limit=20
  → {submissions: [...], total}
```

### 4.4 好词好句 `/api/phrases`
```
GET /api/phrases
  Query: ?source=人民日报&tag=基层治理&page=1&limit=20
  → {phrases: [...], total}

GET /api/phrases/<id>
  → {phrase detail}

POST /api/phrases/<id>/favorite
  Header: Authorization: Bearer <token>
  → {message: "ok"}

DELETE /api/phrases/<id>/favorite
  → {message: "ok"}

GET /api/phrases/favorites
  Header: Authorization: Bearer <token>
  → {phrases: [...]}
```

### 4.5 薄弱点 `/api/weak`
```
GET /api/weak
  Header: Authorization: Bearer <token>
  → {weak_points: [{missing_key, topic_tag, times_missed}]}

GET /api/weak/stats
  → {topic_distribution: {乡村振兴: 5, 基层治理: 3}}
```

### 4.6 管理后台 `/api/admin`
```
GET /api/admin/papers
  Query: ?status=draft&page=1
  → {papers: [...], total}

POST /api/admin/papers
  Body: {paper JSON}
  → {pid}

PUT /api/admin/papers/<pid>
  Body: {paper fields to update}
  → {pid}

DELETE /api/admin/papers/<pid>
  → {message: "deleted"}

GET /api/admin/phrases/pending
  → {phrases: [...]}

POST /api/admin/phrases/<id>/approve
  → {message: "approved"}

POST /api/admin/phrases/<id>/reject
  → {message: "rejected"}

GET /api/admin/users
  Query: ?page=1&role=user
  → {users: [...], total}

PUT /api/admin/users/<uid>/ban
  → {message: "banned"}

GET /api/admin/stats
  → {users_count, papers_count, submissions_today, avg_score}
```

---

## 五、代码模块规范

### 5.1 项目结构

```
src/
├── app.py                    # Flask主入口，路由注册
├── config.py                 # 环境变量配置
├── models/                   # 数据模型（与表一一对应）
│   ├── user.py
│   ├── paper.py
│   ├── submission.py
│   ├── phrase.py
│   └── weak_point.py
├── services/                 # 业务逻辑
│   ├── auth.py              # 注册/登录/JWT
│   ├── paper_service.py     # 试卷CRUD
│   ├── grader/              # AI批改核心
│   │   ├── scorer.py        # 主评分流程
│   │   ├── dimensions.py    # 各维度计算
│   │   ├── cache.py         # 批改缓存
│   │   └── prompts.py       # Prompt模板
│   ├── phrase_service.py
│   └── weak_point_service.py
├── api/                      # Flask Blueprint路由
│   ├── auth.py
│   ├── papers.py
│   ├── submissions.py
│   ├── phrases.py
│   └── admin.py
├── crawler/                  # 爬虫（可选，Phase 2）
│   ├── fenbi.py
│   └── parser.py
└── bot/
    └── telegram_bot.py      # TG Bot命令处理
```

### 5.2 命名规范

- 文件名：小写+下划线（auth_service.py）
- 类名：大驼峰（class UserService）
- 函数名：小写+下划线（get_user_by_id）
- 常量：大写+下划线（MAX_TOKEN_EXPIRE）
- 数据库表名：snake_case（papers, good_phrases）
- API路径：小写+下划线（/api/papers）

### 5.3 错误处理规范

```python
class APIError(Exception):
    def __init__(self, message, code=400):
        self.message = message
        self.code = code

# 所有API统一返回格式：
# 成功：{"data": {...}}  或  {"message": "ok"}
# 失败：{"error": "错误描述", "code": 400}
```

### 5.4 JWT认证装饰器

```python
from functools import wraps
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({"error": "Token required", "code": 401}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = get_user(data['sub'])
            if not current_user:
                return jsonify({"error": "User not found", "code": 401}), 401
            kwargs['current_user'] = current_user
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired", "code": 401}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token", "code": 401}), 401
        return f(*args, **kwargs)
    return decorated
```

---

## 六、AI批改核心（grader/）

### 6.1 评分维度权重

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| 踩点命中 | 40% | ROUGE + 语义相似 + alias匹配 |
| 逻辑结构 | 25% | 分段数、序号词、过渡词 |
| 语言规范 | 20% | 口语化检测+官方用语命中 |
| 字数控制 | 10% | 超出/不足比例 |
| 卷面整洁 | 5% | 标点密度、错字疑似 |

### 6.2 批改缓存策略

```python
# 缓存key = hash(paper_id + question_id + answer_text)
# 缓存有效期：24小时
# 命中缓存直接返回，不调LLM
```

### 6.3 LLM调用策略

```python
MODEL = "gpt-4o-mini"  # 或 "deepseek-chat"
TEMPERATURE = 0.3
MAX_TOKENS = 1000
```

### 6.4 Prompt模板（参考 grader/prompts.py）

- `GRADING_SYSTEM_PROMPT`: 角色设定（资深阅卷老师）
- `GRADING_USER_PROMPT`: 包含题目+用户答案+评分标准
- 输出约束：JSON格式，各维度得分+详细反馈

---

## 七、Telegram Bot 命令

| 命令 | 说明 | 权限 |
|------|------|------|
| `/start` | 欢迎页+快捷按钮 | 所有人 |
| `/login <token>` | 绑定Web账号 | 所有人 |
| `/papers` | 浏览试卷列表 | 已登录 |
| `/exam <pid>` | 开始作答（inline button选择题目） | 已登录 |
| `/my` | 我的学习数据 | 已登录 |
| `/phrases` | 好词好句随手查 | 所有人 |
| `/weak` | 薄弱点统计 | 已登录 |
| `/help` | 帮助说明 | 所有人 |

Bot菜单按钮：`开始作答` / `我的卷库` / `好词好句` / `学习报告`

---

## 八、实现顺序（Phase划分）

### Phase 1: 核心骨架（MVP）
**目标：可运行的最小闭环**
1. 数据库建表 + 初始数据
2. Flask API基础框架（auth + papers + submissions）
3. 前端静态页面（首页+卷库+作答+结果）
4. AI批改核心（单题，模拟数据）
5. Telegram Bot基础交互

**预计：2-3天**

### Phase 2: 卷库扩充
1. 粉笔爬虫模块
2. 更多试卷入库（50+套）
3. 试卷搜索/筛选优化
4. 定时增量抓取

**预计：3-5天**

### Phase 3: 批改质量 + 好词好句
1. 完整AI批改（5维度）
2. 分题型Prompt优化
3. 好词好句系统（来源官媒）
4. 薄弱点追踪

**预计：3-4天**

### Phase 4: 后台管理 + 高级功能
1. 管理后台（试卷管理/好词审核/用户管理/统计）
2. 学习记录+进度追踪
3. 排行榜

**预计：5-7天**

---

## 九、部署规范

### 9.1 端口分配
- SLB Web: `8789`（与 gaokao-number 的 `8789` 端口不同，SLB用`8790`）
- 或通过 Caddy 反代到 `slb.19990419.top`

### 9.2 环境变量
```bash
SECRET_KEY=随机字符串
JWT_SECRET=随机字符串
DATABASE_URL=sqlite:///data/slb.db
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://zyapi.tuluo.top:8888
TG_BOT_TOKEN=your-telegram-bot-token
ADMIN_PASSWORD=admin123456
```

### 9.3 Caddy 配置
```json
{
  "slb.19990419.top": {
    "reverse_proxy": "localhost:8790"
  }
}
```

---

## 十、关键文件清单

| 文件 | 必须/可选 | 说明 |
|------|---------|------|
| `data/schema.sql` | 必须 | 完整建表语句 |
| `data/seed_papers.sql` | 必须 | 3-5套示例卷（Phase1用） |
| `data/seed_phrases.sql` | 必须 | 20条好词初始数据 |
| `src/app.py` | 必须 | Flask主入口 |
| `src/config.py` | 必须 | 配置 |
| `src/services/auth.py` | 必须 | JWT认证 |
| `src/services/grader/scorer.py` | 必须 | AI批改核心 |
| `src/api/papers.py` | 必须 | 试卷API |
| `src/api/submissions.py` | 必须 | 提交批改API |
| `src/bot/telegram_bot.py` | 必须 | TG Bot |
| `templates/index.html` | 必须 | 首页 |
| `templates/exam.html` | 必须 | 作答页 |
| `templates/result.html` | 必须 | 结果页 |
| `templates/admin/` | 必须 | 后台管理页 |
| `static/css/main.css` | 必须 | 主样式 |

---

## 十一、验收标准

- [ ] 用户注册/登录/JWT认证正常
- [ ] 试卷列表+详情可浏览
- [ ] 提交答案后AI批改返回结果
- [ ] 批改结果包含多维度得分+详细反馈
- [ ] 好词好句可收藏
- [ ] 薄弱点自动记录
- [ ] Telegram Bot基本交互正常
- [ ] 管理后台可管理试卷/好词/用户
- [ ] 部署后 `slb.19990419.top` 可访问