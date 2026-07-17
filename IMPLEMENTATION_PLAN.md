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
│       ├── dashboard.html      # 工作台首页
│       ├── users.html          # 用户管理
│       ├── user_detail.html    # 用户详情
│       ├── papers.html         # 试卷管理
│       ├── paper_edit.html     # 试卷编辑
│       ├── phrases.html        # 好词管理
│       ├── reviews.html        # 批改复核
│       ├── stats.html          # 数据统计
│       ├── logs.html           # 操作日志
│       └── settings.html       # 系统设置
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

## 七、管理后台详细设计

### 7.1 管理员角色权限体系

```sql
-- 扩展 users 表的 role 字段
-- 角色：super_admin / admin / reviewer / operator
-- permissions 表
CREATE TABLE admin_roles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    role          TEXT UNIQUE NOT NULL,      -- super_admin, admin, reviewer, operator
    permissions   TEXT NOT NULL,             -- JSON 数组
    description   TEXT,
    created_at    DATETIME DEFAULT NOW
);

-- 初始角色数据
INSERT INTO admin_roles (role, permissions, description) VALUES
('super_admin', '["*"]', '超级管理员，拥有所有权限'),
('admin', '["users.view", "users.edit", "users.ban", "papers.*", "phrases.*", "submissions.*", "stats.view", "logs.view"]', '管理员，核心功能管理'),
('reviewer', '["submissions.review", "submissions.view", "phrases.approve"]', '复核员，批改复核和好词审核'),
('operator', '["papers.add", "papers.edit", "papers.delete", "phrases.add"]', '运维人员，试卷和好词增删改');
```

**权限矩阵：**

| 功能 | super_admin | admin | reviewer | operator |
|------|-------------|-------|----------|----------|
| 用户管理（查看/编辑/封禁） | ✅ | ✅ | ❌ | ❌ |
| 试卷管理（增删改） | ✅ | ✅ | ❌ | ✅ |
| 试卷审核（上下架） | ✅ | ✅ | ❌ | ❌ |
| 好词审核（通过/驳回） | ✅ | ✅ | ✅ | ❌ |
| 批改复核 | ✅ | ✅ | ✅ | ❌ |
| 数据统计 | ✅ | ✅ | ❌ | ❌ |
| 操作日志查看 | ✅ | ✅ | ❌ | ❌ |
| 角色权限管理 | ✅ | ❌ | ❌ | ❌ |
| 系统设置 | ✅ | ❌ | ❌ | ❌ |

**API 层权限装饰器：**
```python
# src/api/utils.py

def admin_required(permission=None):
    """管理员权限装饰器"""
    def decorator(f):
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
                if current_user.role not in ('super_admin', 'admin', 'reviewer', 'operator'):
                    return api_error("Admin access required", 403)
                # 权限检查
                if permission and permission != "*":
                    role_perms = get_role_permissions(current_user.role)
                    if permission not in role_perms and "*" not in role_perms:
                        return api_error("Permission denied", 403)
                kwargs['current_user'] = current_user
            except jwt.ExpiredSignatureError:
                return api_error("Token expired", 401)
            except jwt.InvalidTokenError:
                return api_error("Invalid token", 401)
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_role_permissions(role: str) -> list:
    """获取角色权限列表"""
    row = db.query_one("SELECT permissions FROM admin_roles WHERE role = %s", [role])
    return json.loads(row['permissions']) if row else []
```

---

### 7.2 后台功能模块详细设计

#### 7.2.1 工作台首页（Dashboard）

**路径：** `/admin/`
**权限：** admin, super_admin

**核心指标卡片：**
```
┌─────────────────────────────────────────────────────────────┐
│  今日概览                                                    │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  今日新增用户  │  今日批改数  │  今日收入(预留)│  待复核批改       │
│     23      │    156     │    ¥0       │      12           │
│   ↑ 15%    │   ↑ 8%     │             │  [去处理]         │
└─────────────┴─────────────┴─────────────┴───────────────────┘
```

**图表区域：**
- 近7日/30日批改数量趋势折线图
- 试卷类型分布饼图（国考/省考/事业单位）
- 用户增长趋势图

**快捷入口：**
- 待审核试卷（3套）
- 待审核好词（15条）
- 待复核批改（12条）

---

#### 7.2.2 用户管理

**路径：** `/admin/users`
**权限：** admin, super_admin

**功能列表：**
- 用户列表（支持分页、搜索、筛选角色/状态）
- 用户详情查看（基本信息、VIP状态、学习记录）
- 用户编辑（修改昵称、角色、VIP到期时间）
- 封禁/解封用户
- 强制下线（清除会话）
- 导出用户数据（CSV）

**用户列表表头：**
| 列 | 说明 |
|---|---|
| 用户ID | UUID 前8位 |
| 用户名 | 登录名 |
| 昵称 | 显示名 |
| 角色 | user / vip / admin |
| VIP到期 | 永久/日期/无 |
| 注册时间 | - |
| 最后登录 | - |
| 状态 | active / banned |
| 操作 | 查看/编辑/封禁 |

**筛选条件：**
- 角色：全部 / 普通用户 / VIP / 管理员
- 状态：全部 / 正常 / 已封禁
- 日期范围：注册时间
- 关键词搜索：用户名/昵称

**批量操作：**
- 批量发送通知（预留）
- 批量导出

---

#### 7.2.3 试卷管理

**路径：** `/admin/papers`
**权限：** admin, super_admin, operator

**功能列表：**
- 试卷列表（支持分页、筛选）
- 添加新试卷（表单录入/JSON导入）
- 编辑试卷信息
- 题目管理（增删改题目）
- 上下架控制
- 批量导入（Excel/JSON）
- 试卷预览

**试卷列表表头：**
| 列 | 说明 |
|---|---|
| 试卷ID | - |
| 标题 | - |
| 来源 | 自建/人民日报/... |
| 类型 | 国考/省考/事业单位 |
| 年份 | - |
| 题目数 | - |
| 热度 | 浏览次数 |
| 状态 | 草稿/已发布/已下架 |
| 创建时间 | - |
| 操作 | 预览/编辑/上下架 |

**添加/编辑试卷表单：**
```
基本信息
├── 标题：[_______________]
├── 来源：[下拉选择] 自建 / 人民日报 / 求是网 / 新华网 / 其他
├── 来源URL：[_______________]
├── 考试类型：[国考 ▼]
├── 年份：[2024 ▼]
├── 季节：[全年 ▼]
└── 省份：[全国 ▼]

材料内容
└── 材料（富文本编辑器，支持分段标记）：

题目管理（可拖拽排序）
├── 题目1：[归纳概括] 分数上限[20] 字数限制[150-200]
├── 题目2：[对策建议] 分数上限[35] 字数限制[300-400]
└── [+ 添加题目]

标准答案（每个题目对应）
├── 题目1答案要点：
│   ├── 要点1：[完善基础设施建设] 得分[4] 别名：[修建道路,基础设施]
│   ├── 要点2：[发展特色产业] 得分[5] 别名：[产业多元化]
│   └── [+ 添加要点]
└── ...

高级设置
├── 难度：[1-5]
├── 标签：[乡村振兴,基层治理]（多选/输入）
└── 状态：[草稿 / 已发布]
```

---

#### 7.2.4 好词好句管理

**路径：** `/admin/phrases`
**权限：** admin, super_admin, reviewer

**功能列表：**
- 好词列表（支持筛选状态/来源/标签）
- 审核操作（通过/驳回）
- 批量审核
- 添加好词
- 编辑好词
- 设置热门

**好词列表表头：**
| 列 | 说明 |
|---|---|
| ID | - |
| 好词好句 | 内容预览（截断） |
| 来源 | 人民日报/求是网/... |
| 标签 | 基层治理/乡村振兴/... |
| 热度 | 收藏数 |
| 状态 | 待审核/已通过/已驳回 |
| 创建时间 | - |
| 操作 | 预览/编辑/审核 |

**审核弹窗：**
```
审核好词："基层是一切工作的落脚点，社会治理的重心必须落实到城乡、社区。"
来源：人民日报
标签：基层治理,社会治理

操作：
○ 审核通过
○ 审核驳回
  原因：[________________]

备注：[________________]（可选）

[取消] [确认提交]
```

---

#### 7.2.5 批改复核管理

**路径：** `/admin/reviews`
**权限：** admin, super_admin, reviewer

**功能列表：**
- 待复核列表（AI批改质量抽检）
- 已复核列表
- 复核操作（确认AI结果/人工修正）
- 复核统计

**待复核列表表头：**
| 列 | 说明 |
|---|---|
| 提交ID | - |
| 用户 | 昵称 |
| 试卷 | 标题-题目 |
| AI得分 | - |
| AI批改时间 | - |
| 标记原因 | 低于60分 / 前1000条 / 随机抽检 |
| 操作 | [复核] |

**复核详情页面：**
```
┌─────────────────────────────────────────────────────────────┐
│  提交详情                                        [返回列表]  │
├─────────────────────────────────────────────────────────────┤
│  用户：张三    试卷：2024国考申论（地市级）- 第2题            │
│  提交时间：2024-01-15 14:30                                 │
├─────────────────────────────────────────────────────────────┤
│  用户答案：                                                 │
│  基层治理重点在于...（此处展示完整用户作答）                 │
├─────────────────────────────────────────────────────────────┤
│  AI批改结果：                                               │
│  总分：58/100                                               │
│  ├── 踩点命中：32/40                                        │
│  ├── 逻辑结构：15/25                                        │
│  ├── 语言规范：6/20                                         │
│  ├── 字数控制：5/10                                         │
│  └── 卷面整洁：0/5                                          │
│                                                             │
│  AI反馈：要点遗漏较多，逻辑层次不够清晰...                   │
├─────────────────────────────────────────────────────────────┤
│  人工复核：                                                 │
│  ○ 确认AI结果                                               │
│  ○ 修改AI结果                                               │
│     调整后总分：[58]                                        │
│     调整原因：[________________________________]            │
│                                                             │
│  [取消] [提交复核]                                          │
└─────────────────────────────────────────────────────────────┘
```

---

#### 7.2.6 数据统计

**路径：** `/admin/stats`
**权限：** admin, super_admin

**统计维度：**

1. **用户统计**
   - 总用户数 / 今日新增 / 本月新增
   - VIP用户数及占比
   - 用户留存率（次周留存、次月留存）
   - 用户地域分布（预留）

2. **批改统计**
   - 今日/本周/本月批改总数
   - 平均得分分布
   - 各维度平均得分
   - 缓存命中率

3. **内容统计**
   - 试卷总数 / 题目总数
   - 好词好句总数 / 待审核数
   - 各类型试卷占比

4. **学习行为统计**
   - 人均批改次数
   - 高频使用时段
   - 最热试卷TOP10

**导出功能：**
- 支持导出CSV/Excel格式
- 支持自定义日期范围

---

#### 7.2.7 操作日志

**路径：** `/admin/logs`
**权限：** admin, super_admin

**日志列表表头：**
| 列 | 说明 |
|---|---|
| 时间 | - |
| 管理员 | 昵称 |
| 操作类型 | 登录/编辑用户/审核试卷/... |
| 操作对象 | 具体对象描述 |
| 详情 | JSON格式的变更内容 |
| IP地址 | - |

**筛选条件：**
- 操作类型
- 管理员
- 日期范围

**日志保留策略：**
- 普通操作日志：保留90天
- 敏感操作（登录/封禁/删除）：保留180天
- 超过保留期自动清理

---

### 7.3 后台UI设计规范

**布局结构：**
```
┌──────────────────────────────────────────────────────────────────┐
│  顶部导航栏（固定，高度64px）                                      │
│  ┌──────┬──────────────────────────────────────────┬────────────┐ │
│  │ Logo │  SLB 管理后台                              │ 管理员 ▼   │ │
│  └──────┴──────────────────────────────────────────┴────────────┘ │
├────────────┬─────────────────────────────────────────────────────┤
│  侧边导航   │  主内容区                                            │
│  （宽度    │  ┌──────────────────────────────────────────────┐   │
│   220px）  │  │  页面标题 + 面包屑                    操作按钮  │   │
│            │  ├──────────────────────────────────────────────┤   │
│  📊 工作台  │  │                                              │   │
│  👥 用户    │  │  内容区域                                    │   │
│  📝 试卷    │  │                                              │   │
│  📚 好词    │  │                                              │   │
│  ✓ 批改复核 │  │                                              │   │
│  📈 统计    │  │                                              │   │
│  📋 日志    │  │                                              │   │
│            │  └──────────────────────────────────────────────┘   │
│  ────────  │                                                      │
│  ⚙️ 系统设置│                                                      │
└────────────┴─────────────────────────────────────────────────────┘
```

**配色方案（后台专用）：**
```css
/* static/css/admin.css */
:root {
  /* 后台专用配色 */
  --admin-sidebar-bg: #1A3A6B;      /* 侧边栏背景 */
  --admin-sidebar-active: #2B5BA8;  /* 侧边栏选中态 */
  --admin-sidebar-text: #FFFFFF;    /* 侧边栏文字 */
  --admin-header-bg: #FFFFFF;       /* 顶部栏背景 */
  --admin-content-bg: #F5F7FA;      /* 内容区背景 */
  --admin-card-bg: #FFFFFF;         /* 卡片背景 */

  /* 表格规范 */
  --table-border: #E5E7EB;
  --table-header-bg: #F9FAFB;
  --table-row-hover: #F3F4F6;

  /* 状态色 */
  --status-pending: #F59E0B;   /* 待审核-橙 */
  --status-active: #10B981;    /* 已通过-绿 */
  --status-rejected: #EF4444; /* 已驳回-红 */
  --status-draft: #6B7280;     /* 草稿-灰 */
}
```

**后台组件规范：**

| 组件 | 规范 |
|------|------|
| 侧边导航项 | 高度44px，左侧padding 24px，图标16px，选中态有左侧4px主色边框 |
| 数据表格 | 表头14px粗体，内容14px正常，行高52px，hover高亮 |
| 操作按钮 | 主操作用主色，次操作用描边样式，危险操作用红色 |
| 状态标签 | 圆角12px，padding 4px 12px，字体12px |
| 分页器 | 右对齐，每页条数可选（20/50/100） |
| 筛选表单 | 行内表单，筛选项紧凑排列，重置按钮在右侧 |

---

### 7.4 后台管理完整API列表

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| **工作台** | | | |
| GET | `/api/admin/dashboard` | admin | 获取仪表盘数据 |
| GET | `/api/admin/stats` | admin | 全局统计 |
| **用户管理** | | | |
| GET | `/api/admin/users` | admin | 用户列表（分页/筛选） |
| GET | `/api/admin/users/<uid>` | admin | 用户详情 |
| PUT | `/api/admin/users/<uid>` | admin | 编辑用户 |
| PUT | `/api/admin/users/<uid>/ban` | admin | 封禁/解封用户 |
| DELETE | `/api/admin/users/<uid>/sessions` | admin | 强制下线 |
| **试卷管理** | | | |
| GET | `/api/admin/papers` | admin | 试卷列表（分页/筛选） |
| POST | `/api/admin/papers` | admin | 添加试卷 |
| GET | `/api/admin/papers/<pid>` | admin | 试卷详情 |
| PUT | `/api/admin/papers/<pid>` | admin | 编辑试卷 |
| DELETE | `/api/admin/papers/<pid>` | admin | 删除试卷 |
| PUT | `/api/admin/papers/<pid>/publish` | admin | 发布/下架 |
| **好词管理** | | | |
| GET | `/api/admin/phrases` | admin | 好词列表（分页/筛选） |
| POST | `/api/admin/phrases` | admin | 添加好词 |
| GET | `/api/admin/phrases/<id>` | admin | 好词详情 |
| PUT | `/api/admin/phrases/<id>` | admin | 编辑好词 |
| DELETE | `/api/admin/phrases/<id>` | admin | 删除好词 |
| POST | `/api/admin/phrases/<id>/approve` | admin | 审核通过 |
| POST | `/api/admin/phrases/<id>/reject` | admin | 审核驳回 |
| POST | `/api/admin/phrases/batch/approve` | admin | 批量审核通过 |
| **批改复核** | | | |
| GET | `/api/admin/submissions/pending_review` | reviewer | 待复核列表 |
| GET | `/api/admin/submissions/reviewed` | reviewer | 已复核列表 |
| GET | `/api/admin/submissions/<sid>` | reviewer | 复核详情 |
| POST | `/api/admin/submissions/<sid>/review` | reviewer | 提交复核结果 |
| **日志** | | | |
| GET | `/api/admin/logs` | admin | 操作日志（分页/筛选） |
| **系统设置** | | | |
| GET | `/api/admin/settings` | super_admin | 获取设置 |
| PUT | `/api/admin/settings` | super_admin | 修改设置 |

---

### 7.5 数据库Schema扩展

```sql
-- admin_roles 表（如上）
CREATE TABLE admin_roles (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    role          TEXT UNIQUE NOT NULL,
    permissions   TEXT NOT NULL,
    description   TEXT,
    created_at    DATETIME DEFAULT NOW
);

-- admin_sessions 表（后台登录会话独立）
CREATE TABLE admin_sessions (
    sid       TEXT PRIMARY KEY,
    uid       TEXT NOT NULL,
    token     TEXT UNIQUE NOT NULL,
    ip        TEXT,
    created_at DATETIME DEFAULT NOW,
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- 操作日志表（如AGENTS.md所示，已有）

-- users表已有role字段，无需修改
-- 但需要确认super_admin角色的初始数据
INSERT INTO users (uid, username, password_hash, nickname, role, status)
VALUES ('admin_00000001', 'admin', '$2b$12$...', '超级管理员', 'super_admin', 'active');
```

---

### 7.6 超级管理员初始账户

```python
# 初始化脚本创建超级管理员
# 用户名：admin
# 密码：通过环境变量 ADMIN_PASSWORD 设置，首次登录强制修改

# .env
# ADMIN_PASSWORD=change-me-after-deploy
```

---

## 八、API 接口详细规范

### 8.1 统一响应格式

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

### 8.2 核心 API 列表

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

---

## 九、部署规范

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

## 九、部署规范

### 9.1 端口与域名

| 服务 | 端口 | 域名 |
|------|------|------|
| SLB Web | `8790` | `slb.19990419.top` |
| Redis | `6379` | localhost |
| Telegram Bot | webhook | `https://slb.19990419.top/api/bot` |

### 9.2 环境变量

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

### 9.3 Caddy 配置

```json
{
  "slb.19990419.top": {
    "reverse_proxy": "localhost:8790",
    "tls": "letsencrypt"
  }
}
```

### 9.4 健康检查

```bash
# 部署后验证
curl https://slb.19990419.top/api/papers | jq .total  # 应返回试卷总数
curl https://slb.19990419.top/                          # 应返回首页HTML
```

---

## 十、验收标准

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

## 十一、风险登记册

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| DeepSeek API 限流 | 中 | 高 | Redis 缓存兜底，key 轮换 |
| 批改质量不足 | 中 | 高 | 前1000条人工抽检，用户纠错通道 |
| 版权争议 | 低 | 高 | Phase 1-2 全自建题，不爬竞品 |
| Telegram Bot 被封 | 低 | 中 | Web 为主，Bot 为辅 |
| 会员转化率低 | 中 | 中 | 先免费试用，再引导付费 |

---

*本文档为执行蓝图，所有技术决策均已标注。Codex 可直接按本文件构建代码，无需二次确认。*