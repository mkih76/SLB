# SLB 申论AI批改平台 · 实施细则 v1.0

> 文档版本：v1.0  
> 创建时间：2026-05-26  
> 状态：待执行  
> 目标：作为 Claude Code/Codex 的执行蓝图，实现 P0→P1→P2→P3 四阶段并行推进

---

## 一、总体架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户层                              │
│  Web (slb.19990419.top)  │  Telegram Bot  │  管理后台     │
├─────────────────────────────────────────────────────────┤
│                      API 网关层                          │
│              Flask REST API + JWT Auth                   │
├──────────────┬──────────────────┬───────────────────────┤
│   服务层      │   服务层          │   服务层               │
│  grader/     │  paper_service/  │  phrase_service/       │
│  (AI批改)    │  (试卷管理)       │  (好词好句)            │
├──────────────┴──────────────────┴───────────────────────┤
│                      数据层                              │
│         SQLite + Redis 缓存  │  好词/薄弱点追踪           │
└─────────────────────────────────────────────────────────┘
```

**并行策略：** 三条独立线可同步启动  
- **线A（前端）**：UI系统化 + 避免AI味 + 动效  
- **线B（架构）**：缓存机制 + Token控制 + DeepSeek V3 切换  
- **线C（产品）**：免费边界 + 功能演示 + 纠错通道

---

## 二、UI/UX 专业化提升实施细则

### 2.1 字体体系

**目标：** 权威感 + 专业感，避免"AI廉价感"

```css
/* static/css/variables.css */
:root {
  /* 字体 */
  --font-title: 'Noto Serif SC', 'Source Han Serif CN', '思源宋体', serif;
  --font-body: 'Noto Sans SC', 'Source Han Sans CN', '思源黑体', sans-serif;
  --font-code: 'JetBrains Mono', 'Roboto Mono', monospace;

  /* 字号 */
  --text-xs: 12px;
  --text-sm: 14px;
  --text-base: 16px;
  --text-lg: 18px;
  --text-xl: 22px;
  --text-2xl: 28px;
  --text-3xl: 36px;

  /* 颜色体系 */
  --color-primary: #1A3A6B;
  --color-primary-light: #2B5BA8;
  --color-accent: #C9A84C;
  --color-bg: #F5F7FA;
  --color-card: #FFFFFF;
  --color-text: #1F2937;
  --color-text-secondary: #6B7280;
  --color-success: #059669;
  --color-warning: #D97706;
  --color-error: #DC2626;
}
```

**实施步骤：**
1. 在 `templates/base.html` 的 `<head>` 中引入 Google Fonts：
   ```html
   <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Noto+Serif+SC:wght@600;700&display=swap" rel="stylesheet">
   ```
2. 全局 CSS 覆盖：
   ```css
   h1, h2, h3 { font-family: var(--font-title); }
   body, p, li { font-family: var(--font-body); }
   ```
3. 标题用思源宋体，正文用思源黑体，不允许混用

### 2.2 微交互动效规范

**目标：** 悬停上浮 + 按压反馈 + 色变过渡，禁止过度圆润

```css
/* static/css/interactions.css */

/* 卡片悬停：上浮 + 阴影加深 */
.card {
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  transition: transform 200ms ease, box-shadow 200ms ease;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* 按钮按压效果 */
.btn-primary {
  background: var(--color-primary);
  border-radius: 6px;
  transition: background 200ms ease, transform 80ms ease;
}
.btn-primary:hover {
  background: var(--color-primary-light);
}
.btn-primary:active {
  transform: scale(0.97);
}

/* 输入框聚焦边框过渡 */
.input-field {
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  transition: border-color 200ms ease, box-shadow 200ms ease;
}
.input-field:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(26,58,107,0.1);
  outline: none;
}

/* 表单验证失败 shake 动画 */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
}
.input-error {
  animation: shake 400ms ease;
  border-color: var(--color-error);
}

/* Loading 态 */
.btn-loading {
  position: relative;
  pointer-events: none;
  opacity: 0.7;
}
.btn-loading::after {
  content: '';
  position: absolute;
  width: 16px; height: 16px;
  top: 50%; left: 50%;
  margin: -8px 0 0 -8px;
  border: 2px solid transparent;
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 600ms linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

### 2.3 间距系统（8px 基准网格）

```css
:root {
  --space-1: 8px;   /* 8px 基准 */
  --space-2: 16px;  /* 16px */
  --space-3: 24px;  /* 24px */
  --space-4: 32px;  /* 32px */
  --space-6: 48px;  /* 48px */
  --space-8: 64px;  /* 64px */
}

/* 所有间距必须是 8 的倍数 */
.card { padding: var(--space-3); }        /* 24px */
.section { margin-bottom: var(--space-4); } /* 32px */
.page-container { padding: var(--space-4) var(--space-3); }
```

### 2.4 避免"AI味"清单

| 规则 | 具体要求 | 检查 |
|------|---------|------|
| 圆角 | 所有卡片/按钮圆角 4-8px，禁止 16px+ | `border-radius: 6px` |
| 渐变 | 禁止在主色/按钮上使用 gradient | 搜索 `gradient` 报错 |
| 文字对齐 | 正文区块左对齐，禁止居中（标题除外） | `text-align: left` |
| 图标 | 使用 Lucide Icons CDN，禁止 emoji | Lucide CDN |
| 间距 | 内容区左右 padding ≥ 24px | CSS 检查 |
| 对话式UI | 禁止"你好，我是AI助手"式开场白 | 无 chat 气泡 |

**实施清单：**
- [ ] 引入 Lucide Icons: `https://unpkg.com/lucide@latest`
- [ ] 清理所有 emoji 表情，改用 SVG 图标
- [ ] 搜索全站 `border-radius`，超过 12px 的报错
- [ ] 表单/内容区域强制 `text-align: left`

---

## 三、会员体系实施细则

### 3.1 免费/会员功能边界

```
┌──────────────────────────────────────────────────┐
│                  免费用户                         │
│  ✅ 完整体验一次考试流程（注册→选卷→作答→批改→结果）  │
│  ✅ 查看本次批改结果（单维度）                      │
│  ❌ 详细多维度分析                                │
│  ❌ 薄弱点追踪                                    │
│  ❌ 学习报告                                      │
│  ❌ 好词好句收藏                                  │
├──────────────────────────────────────────────────┤
│                  会员用户                         │
│  ✅ 所有功能                                      │
│  ✅ 详细反馈（5维度全开）                         │
│  ✅ 薄弱点统计                                    │
│  ✅ 学习报告                                      │
│  ✅ 好词好句收藏                                  │
│  ✅ 优先体验新功能                                │
└──────────────────────────────────────────────────┘
```

**数据库字段扩展：**
```sql
-- users 表已有 vip_expire，新增：
ALTER TABLE users ADD COLUMN free_trial_used INT DEFAULT 0;
```

**API 层拦截逻辑：**
```python
# src/api/utils.py

def check_vip_feature(feature_name: str, current_user):
    """检查用户是否有权限使用某功能"""
    if current_user.role in ('admin', 'vip'):
        return True
    # 免费用户检查试用状态
    if feature_name in ('detailed_feedback', 'weak_tracking', 'report'):
        if not current_user.free_trial_used:
            return {"allowed": False, "upgrade": True}
    return True
```

### 3.2 功能演示入口（无需登录）

**设计：** 登录前用户可以看到"试用一下"按钮，跳过注册直接作答任意一套示范卷

```html
<!-- templates/index.html -->
<div class="demo-entry">
  <a href="/demo" class="btn-demo">
    <i data-lucide="play-circle"></i>
    免注册，试用示范卷
  </a>
</div>
```

**路由：**
- `GET /demo` → 渲染 `demo.html`（免登录）
- `POST /demo/submit` → 作答提交，答案不存储，仅展示本次结果
- 结果页显示"登录后可保存记录"，引导注册

---

## 四、技术风险解决方案

### 4.1 LLM API 成本控制（三步走）

**Step 1：切换 DeepSeek V3**
```python
# src/config.py

LLM_PROVIDER = "deepseek"
LLM_MODEL = "deepseek-chat"
LLM_BASE_URL = "https://api.deepseek.com/v1"  # 或沿用 zyapi 代理
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY", os.getenv("LLM_API_KEY"))
# 成本：DeepSeek V3 $0.27/M tokens vs GPT-4o-mini $0.15/1M tokens
# 但 DeepSeek 质量好且中文教育场景更适配
```

**Step 2：答案缓存（Redis）**
```python
# src/services/grader/cache.py

import hashlib, json, redis

cache = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
CACHE_TTL = 86400  # 24小时

def get_cached_result(pid: str, qid: str, answer: str):
    key = hashlib.sha256(f"{pid}:{qid}:{answer}".encode()).hexdigest()
    cached = cache.get(f"grader:{key}")
    return json.loads(cached) if cached else None

def set_cached_result(pid: str, qid: str, answer: str, result: dict):
    key = hashlib.sha256(f"{pid}:{qid}:{answer}".encode()).hexdigest()
    cache.setex(f"grader:{key}", CACHE_TTL, json.dumps(result))

# 命中缓存时日志：
# logger.info(f"Cache hit for {pid}:{qid}, skipped LLM call")
```

**Step 3：Token 控制**
```python
# src/services/grader/scorer.py

MAX_HISTORY_TOKENS = 3000  # 超出截断

def truncate_context(messages: list, max_tokens=MAX_HISTORY_TOKENS):
    """截断过长历史，避免超出限额"""
    total = sum(len(m['content']) for m in messages)
    while total > max_tokens * 4:  # 粗估 4 字符/token
        removed = messages.pop(0)
        total -= len(removed['content'])
    return messages

def check_max_tokens(prompt: str, max_limit=4000):
    """单次请求前检查，超限直接拒绝"""
    if len(prompt) > max_limit * 4:
        raise ValueError(f"Prompt exceeds {max_limit} tokens, rejected")
```

### 4.2 批改质量保障体系

**人工抽检机制：**
```sql
-- submissions 表已有 is_reviewed 字段，新增：
ALTER TABLE submissions ADD COLUMN needs_review INT DEFAULT 0;
ALTER TABLE submissions ADD COLUMN reviewer_uid TEXT;
```

```python
# src/services/grader/scorer.py

# 前1000次批改全部标记需人工复核
def should_review(submission, total_count):
    return total_count < 1000 or submission.score < 60

# 管理员复核路由
@admin_bp.route('/submissions/pending_review')
def pending_review_list():
    submissions = db.query("""
        SELECT s.*, u.nickname FROM submissions s
        JOIN users u ON s.uid = u.uid
        WHERE s.needs_review = 1 AND s.is_reviewed = 0
        ORDER BY s.created_at DESC LIMIT 50
    """)
    return render_template('admin/review_list.html', submissions=submissions)
```

**用户纠错通道：**
```html
<!-- templates/result.html -->
<div class="feedback-section">
  <p>认为批改有误？</p>
  <button id="btn-feedback" class="btn-secondary">
    <i data-lucide="message-square"></i>
    提交纠错
  </button>
</div>

<div id="feedback-form" class="hidden">
  <textarea id="feedback-text" placeholder="请说明你的理由..."></textarea>
  <button id="btn-submit-feedback">提交</button>
</div>
```

```python
# src/api/submissions.py

@submissions_bp.route('/<sid>/feedback', methods=['POST'])
@token_required
def submit_feedback(sid, current_user):
    data = request.json
    db.execute("""
        INSERT INTO admin_logs (admin_uid, action, target_type, target_id, detail)
        VALUES ('system', 'user_feedback', 'submission', %s, %s)
    """, [sid, json.dumps({"uid": current_user['uid'], "content": data['text']})])
    return {"message": "感谢反馈，我们会尽快核实"}
```

### 4.3 版权合规方案

**短期（Phase 1-2）：**
- 不爬取竞品（粉笔/中公/华图）原题
- 使用政府公开文件自己出题：
  - 中央机关及其直属机构年度考试录用公务员公告
  - 各省人民政府官网政策文件
  - 人民日报/求是网时评文章
- 所有题目标注来源：`"source": "自建"` 或 `"source": "人民日报"`

**中期（Phase 3+）：**
- 联系粉笔/中公谈版权授权
- 或接入政府公开 API 数据源

---

## 五、开发优先级与阶段划分

### Phase 0：基础设施（Week 0-1）

**目标：** 可运行的最小闭环，2-3天

```
并行任务清单：
□ 数据库 schema 初始化 + 种子数据（3套示范卷）
□ Flask API 骨架（auth + papers + submissions）
□ 前端静态页面（首页 + 卷库列表 + 作答页 + 结果页）
□ AI 批改核心 mock（返回预设分数，不调LLM）
```

**验收：**
- `curl localhost:8790/api/papers` 返回试卷列表
- 登录 → 选卷 → 作答 → 看到结果页

### Phase 1：核心功能（Week 1-2）

**目标：** 完整 AI 批改流程上线

```
并行任务清单（3条线）：

线A - 前端：
  □ UI 变量体系（CSS变量 + 8px网格）
  □ 动效实现（card悬停/button按压/shake）
  □ 字体升级（引入思源宋体/黑体）
  □ Lucide 图标替换 emoji
  □ 避免AI味审核（圆角/渐变/对齐检查）

线B - 架构：
  □ DeepSeek V3 接入
  □ Redis 缓存层
  □ Token 控制逻辑
  □ 批改质量监控埋点

线C - 产品：
  □ 免费边界 API 拦截
  □ /demo 演示入口
  □ 用户纠错通道
  □ 人工抽检流程
```

**验收：**
- UI 通过 3 人盲测（无AI廉价感）
- 同题缓存命中跳过 LLM
- DeepSeek V3 响应 P99 < 5秒

### Phase 2：卷库扩充（Week 2-3）

**目标：** 50+ 套试卷入库

```
任务清单：
□ 爬虫模块开发（先自建题目，版权确认后扩展粉笔）
□ 试卷搜索/筛选（exam_type + year + province + tag）
□ 题目分类（归纳概括/对策/应用文/议论文）
□ 定时增量脚本（可选，Phase 3再说）
□ 好词好句系统（20条初始数据）
□ 薄弱点追踪（自动记录遗漏关键词）
□ Telegram Bot 命令完善
```

**验收：**
- 试卷总数 ≥ 50
- 好词好句可收藏
- 薄弱点统计可查看

### Phase 3：运营功能（Week 3-4）

**目标：** 会员体系 + 管理后台

```
任务清单：
□ VIP 权限体系完整实现
□ 管理后台（试卷管理/好词审核/用户管理/统计）
□ 学习报告生成
□ 排行榜
□ 续费动机设计（专属功能标识）
□ 退款机制（预留接口，资质到位后接入）
```

**验收：**
- 会员转化率 > 5%
- 管理后台全功能可用

---

## 六、文件结构（最终态）

```
SLB/
├── data/
│   ├── schema.sql              # 完整建表语句
│   ├── seed_papers.sql         # 3套示范卷初始数据
│   └── seed_phrases.sql        # 20条好词初始数据
├── src/
│   ├── app.py                  # Flask 主入口
│   ├── config.py               # 环境变量配置
│   ├── models/                 # 数据模型
│   │   ├── user.py
│   │   ├── paper.py
│   │   ├── submission.py
│   │   ├── phrase.py
│   │   └── weak_point.py
│   ├── services/              # 业务逻辑
│   │   ├── auth.py            # JWT 注册/登录/会话
│   │   ├── paper_service.py   # 试卷 CRUD
│   │   ├── grader/            # AI 批改核心
│   │   │   ├── __init__.py
│   │   │   ├── scorer.py      # 主评分流程
│   │   │   ├── dimensions.py  # 各维度计算
│   │   │   ├── cache.py       # Redis 缓存
│   │   │   └── prompts.py     # Prompt 模板
│   │   ├── phrase_service.py
│   │   └── weak_point_service.py
│   ├── api/                   # Flask Blueprint 路由
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── papers.py
│   │   ├── submissions.py
│   │   ├── phrases.py
│   │   └── admin.py
│   ├── crawler/              # 爬虫（Phase 2）
│   │   ├── fenbi.py
│   │   └── parser.py
│   └── bot/
│       └── telegram_bot.py   # TG Bot
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── papers.html
│   ├── exam.html             # 作答页
│   ├── result.html           # 结果页（含纠错入口）
│   ├── demo.html             # 免登录演示页
│   └── admin/
│       ├── dashboard.html
│       ├── review_list.html
│       ├── papers.html
│       └── phrases.html
├── static/
│   ├── css/
│   │   ├── variables.css     # CSS 变量（颜色/字体/间距）
│   │   ├── interactions.css  # 动效
│   │   ├── main.css          # 主样式
│   │   └── admin.css         # 后台样式
│   └── js/
│       ├── app.js             # 主逻辑
│       ├── exam.js            # 作答页逻辑
│       └── admin.js           # 后台逻辑
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 七、API 接口详细规范

### 7.1 统一响应格式

```python
# src/api/utils.py

def api_success(data=None, message="ok"):
    return jsonify({"data": data, "message": message}), 200

def api_error(message, code=400):
    return jsonify({"error": message, "code": code}), code

# 认证装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return api_error("Token required", 401)
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user = User.get(data['sub'])
            if not current_user:
                return api_error("User not found", 401)
            kwargs['current_user'] = current_user
        except jwt.ExpiredSignatureError:
            return api_error("Token expired", 401)
        except jwt.InvalidTokenError:
            return api_error("Invalid token", 401)
        return f(*args, **kwargs)
    return decorated
```

### 7.2 核心 API 列表

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 否 | 注册 |
| POST | `/api/auth/login` | 否 | 登录 |
| POST | `/api/auth/logout` | 是 | 登出 |
| GET | `/api/auth/me` | 是 | 当前用户 |
| GET | `/api/papers` | 否 | 试卷列表（支持分页/筛选） |
| GET | `/api/papers/<pid>` | 否 | 试卷详情 |
| GET | `/api/papers/<pid>/question/<qid>` | 否 | 题目详情 |
| POST | `/api/submissions` | 是 | 提交批改 |
| GET | `/api/submissions/<sid>` | 是 | 批改结果 |
| POST | `/api/submissions/<sid>/feedback` | 是 | 用户纠错 |
| GET | `/api/submissions/history` | 是 | 历史记录 |
| GET | `/api/phrases` | 否 | 好词好句列表 |
| POST | `/api/phrases/<id>/favorite` | 是 | 收藏 |
| DELETE | `/api/phrases/<id>/favorite` | 是 | 取消收藏 |
| GET | `/api/weak` | 是 | 薄弱点统计 |
| GET | `/api/weak/stats` | 是 | 薄弱点分布 |
| GET | `/api/admin/stats` | admin | 全局统计 |
| GET | `/api/admin/submissions/pending_review` | admin | 待复核列表 |
| POST | `/api/admin/submissions/<sid>/review` | admin | 复核操作 |

---

## 八、部署规范

### 8.1 端口与域名

| 服务 | 端口 | 域名 |
|------|------|------|
| SLB Web | `8790` | `slb.19990419.top` |
| Redis | `6379` | localhost |
| Telegram Bot | webhook | `https://slb.19990419.top/api/bot` |

### 8.2 环境变量

```bash
# .env（不提交到仓库）
SECRET_KEY=your-256bit-secret
JWT_SECRET=your-jwt-secret
DATABASE_URL=sqlite:///data/slb.db
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
TG_BOT_TOKEN=your-telegram-bot-token
REDIS_HOST=localhost
REDIS_PORT=6379
ADMIN_PASSWORD=change-me-after-deploy
```

### 8.3 Caddy 配置

```json
{
  "slb.19990419.top": {
    "reverse_proxy": "localhost:8790",
    "tls": "letsencrypt"
  }
}
```

### 8.4 健康检查

```bash
# 部署后验证
curl https://slb.19990419.top/api/papers | jq .total  # 应返回试卷总数
curl https://slb.19990419.top/                          # 应返回首页HTML
```

---

## 九、验收标准

| 阶段 | 标准 | 检测方法 |
|------|------|---------|
| Phase 0 | 核心闭环跑通，注册→批改→结果 | E2E 测试 |
| Phase 1 | UI 无AI廉价感（3人盲测通过） | 盲测问卷 |
| Phase 1 | LLM 成本降低 90%+（缓存命中 ≥ 30%） | 日志统计 |
| Phase 1 | 批改 P99 延迟 < 5秒 | APM 埋点 |
| Phase 1 | 人工抽检合格率 > 90% | 前1000条人工复核 |
| Phase 2 | 试卷总数 ≥ 50 | `SELECT COUNT(*) FROM papers` |
| Phase 2 | 好词可收藏，薄弱点可统计 | API 测试 |
| Phase 3 | 会员体系完整 | 功能测试 |
| Phase 3 | 管理后台全功能 | 冒烟测试 |

---

## 十、风险登记册

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| DeepSeek API 限流 | 中 | 高 | Redis 缓存兜底，key 轮换 |
| 批改质量不足 | 中 | 高 | 前1000条人工抽检，用户纠错通道 |
| 版权争议 | 低 | 高 | Phase 1-2 全自建题，不爬竞品 |
| Telegram Bot 被封 | 低 | 中 | Web 为主，Bot 为辅 |
| 会员转化率低 | 中 | 中 | 先免费试用，再引导付费 |

---

*本文档为执行蓝图，所有技术决策均已标注。Codex 可直接按本文件构建代码，无需二次确认。*