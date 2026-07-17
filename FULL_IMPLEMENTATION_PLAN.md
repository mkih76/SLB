# SLB 全生命周期闭环实施方案

**版本：** v2.0
**日期：** 2026-05-27
**作者：** SLB 产品设计团队

---

## 总体架构：闭环逻辑

```
用户进入 → 能力诊断（我是谁）
    ↓
制定计划（我要去哪）
    ↓
分题型训练（怎么去）
    ↓
AI 批改 + 诊断报告（到了没有）
    ↓
薄弱点追踪 + 素材补强（哪里没到）
    ↓
再训练 → 循环
```

每个板块都不是孤立功能，而是闭环上的一个环节，环节之间通过数据流转串联。

---

## 板块一：五大题型专项训练系统

### 1.1 设计目标

申论考五种题型，每种题型的评分逻辑完全不同。目前批改是通用的，用户无法针对性提升。本板块的目标是：**让用户按题型拆解练习，每种题型独立计分、独立追踪进步曲线。**

### 1.2 数据库变更

现有 `papers` 表的 `questions` 字段是 JSON 数组，每个 question 已经有 `type` 字段。需要新增两张表：

```sql
-- 题型能力画像表：记录用户每种题型的累计表现
CREATE TABLE user_question_type_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    question_type TEXT NOT NULL,  -- guina/zonghe/duice/zhixing/zuowen
    total_attempts INT DEFAULT 0,
    total_score REAL DEFAULT 0,
    avg_score REAL DEFAULT 0,
    best_score REAL DEFAULT 0,
    last_attempt_at DATETIME,
    dimension_breakdown TEXT DEFAULT '{}',  -- JSON: 各维度平均分
    level TEXT DEFAULT 'bronze',  -- bronze/silver/gold/platinum/diamond
    created_at DATETIME DEFAULT datetime('now'),
    updated_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid),
    UNIQUE(uid, question_type)
);

-- 题型训练记录表：每次训练的详细数据
CREATE TABLE question_type_drills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    question_type TEXT NOT NULL,
    pid TEXT NOT NULL,
    qid TEXT NOT NULL,
    sid TEXT,               -- 关联 submissions 表
    score REAL,
    dimension_scores TEXT,  -- JSON
    key_point_hit_rate REAL, -- 踩点率
    time_spent INT,         -- 用时（秒）
    created_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (pid) REFERENCES papers(pid)
);
CREATE INDEX idx_drills_uid_type ON question_type_drills(uid, question_type);
```

### 1.3 五种题型的 AI 批改 Prompt 设计

这是核心竞争力。每种题型需要独立的 Prompt 模板：

#### 归纳概括题 Prompt

```
你是申论阅卷专家。请对以下归纳概括题进行评分。

【材料】{material}
【题目】{question}
【参考要点】{answer_keys}
【考生答案】{user_answer}

评分维度：
1. 踩点完整度（50分）：逐条对照参考要点，标注命中的要点和遗漏的要点
2. 语言简洁度（25分）：是否废话过多、是否照抄材料原文
3. 归纳准确度（25分）：概括是否准确反映了材料原意

输出 JSON：
{
  "score": 0-100,
  "dimension_scores": {"point_coverage": 0-50, "conciseness": 0-25, "accuracy": 0-25},
  "hit_points": ["要点1原文", "要点2原文"],
  "missing_points": ["遗漏要点1", "遗漏要点2"],
  "detail_feedback": "逐条分析...",
  "improvement_suggestions": ["建议1", "建议2"]
}
```

#### 综合分析题 Prompt

```
评分维度：
1. 分析深度（30分）：是否理解了材料的本质含义
2. 逻辑链完整性（35分）：是否呈现"表现→原因→影响→对策"的完整链条
3. 观点明确度（20分）：是否有清晰的总论点和分论点
4. 语言规范性（15分）

重点检查：逻辑链是否断裂、各层次是否有材料支撑、是否存在循环论证
```

#### 提出对策题 Prompt

```
评分维度：
1. 针对性（30分）：对策是否对得上问题
2. 可行性（25分）：是否在现实条件下可执行
3. 具体性（25分）：是否有"主体+手段+内容"的完整结构
4. 全面性（20分）：是否覆盖了主要问题

重点检查：对策是否假大空、是否有"加强宣传教育"等万能废话、是否有具体操作步骤
```

#### 贯彻执行题 Prompt

```
评分维度：
1. 格式正确性（20分）：标题、称谓、落款是否符合文种要求
2. 目的达成度（30分）：是否完成了题目要求的写作目的
3. 内容完整性（30分）：背景、主体、结尾是否齐全
4. 语言得体性（20分）：语气是否符合文种和对象

文种库：讲话稿、倡议书、调研报告、工作方案、短评、导言、编者按、公开信、简报
每种文种有独立的格式要求，在批改时对照
```

#### 大作文 Prompt

```
评分维度：
1. 立意准确度（25分）：中心论点是否切合题意和材料
2. 论证充实度（25分）：论据是否充分、论证方法是否多样
3. 结构完整性（20分）：标题、开头、分论点段落、结尾是否完整
4. 语言表达（20分）：是否有申论语感、是否口语化
5. 卷面整洁度（10分）：根据字数和格式推断

重点关注：总论点与分论点的逻辑关系、论据是否来自材料或时政、结尾是否有升华
```

### 1.4 前端页面

**题型选择页 `/drill`：**

```
┌─────────────────────────────────────────────────┐
│                 专项训练                          │
├──────────┬──────────┬──────────┬──────────┬──────┤
│ 归纳概括  │ 综合分析  │ 提出对策  │ 贯彻执行  │ 大作文│
│ ★★★☆    │ ★★☆☆    │ ★★★★    │ ★★☆☆    │ ★★★☆│
│ 白银段位  │ 青铜段位  │ 黄金段位  │ 青铜段位  │ 白银 │
│ 均分 72   │ 均分 58   │ 均分 81   │ 均分 55   │ 均分68│
│ 练习12次  │ 练习5次   │ 练习18次  │ 练习3次   │ 练习8次│
└──────────┴──────────┴──────────┴──────────┴──────┘
```

**段位升级规则：**

| 段位 | 条件 |
|------|------|
| 青铜 | 初始 |
| 白银 | 该题型练习 ≥5 次 且 均分 ≥60 |
| 黄金 | 练习 ≥15 次 且 均分 ≥75 |
| 铂金 | 练习 ≥30 次 且 均分 ≥85 |
| 钻石 | 练习 ≥50 次 且 均分 ≥90 |

### 1.5 API 设计

```
GET  /api/drill/types                    -- 获取五种题型的统计数据
GET  /api/drill/recommend?type=guina     -- 获取该题型推荐练习题
POST /api/drill/submit                   -- 提交训练作答（复用 submissions 流程）
GET  /api/drill/history?type=guina&page=1 -- 训练历史
GET  /api/drill/progress?type=guina      -- 进步趋势图数据
```

### 1.6 与闭环的衔接

- **输入来源**：诊断报告的薄弱题型 → 自动推荐对应训练
- **输出去向**：训练结果 → 更新 `user_question_type_stats` → 刷新诊断报告 → 更新备考计划

---

## 板块二：真题库 + 全真模拟考场

### 2.1 设计目标

解决用户"找不到题"和"练习不逼真"的痛点。提供**按年份/省份/题型筛选的真题库**和**限时倒计时的全真模拟环境**。

### 2.2 数据库变更

现有 `papers` 表已经覆盖了大部分字段，需要补充：

```sql
-- 在 papers 表上扩展字段
ALTER TABLE papers ADD COLUMN is_simulation INTEGER DEFAULT 0;  -- 是否为模拟卷
ALTER TABLE papers ADD COLUMN time_limit INT DEFAULT 150;       -- 限时（分钟）
ALTER TABLE papers ADD COLUMN attempt_count INT DEFAULT 0;      -- 答题人次
ALTER TABLE papers ADD COLUMN avg_score REAL DEFAULT 0;         -- 平均分

-- 模拟考试记录表
CREATE TABLE simulation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    pid TEXT NOT NULL,
    started_at DATETIME NOT NULL,
    submitted_at DATETIME,
    time_spent INT,              -- 实际用时（秒）
    total_score REAL,
    question_scores TEXT,        -- JSON: {"qid1": 72, "qid2": 65, ...}
    rank_percentile REAL,        -- 在同卷考生中的排名百分位
    status TEXT DEFAULT 'in_progress',  -- in_progress/submitted/timeout
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (pid) REFERENCES papers(pid)
);
CREATE INDEX idx_sim_uid ON simulation_records(uid);
CREATE INDEX idx_sim_pid ON simulation_records(pid);
```

### 2.3 真题库数据结构

每套真题的 JSON 结构（已存在于 `papers.questions`，标准化如下）：

```json
{
  "qid": "q1",
  "type": "guina",
  "type_name": "归纳概括",
  "question_text": "根据给定资料1，概括S市在推动基层社会治理方面的主要做法。",
  "requirement": "全面、准确、有条理",
  "word_limit": {"min": 100, "max": 200},
  "score": 15,
  "scoring_rubric": [
    {"point": "党建引领，建立社区党组织", "keywords": ["党建", "党组织"], "score": 3},
    {"point": "搭建居民议事平台", "keywords": ["议事", "协商"], "score": 3}
  ]
}
```

### 2.4 全真模拟考场流程

```
1. 用户选择试卷 → 进入等待页（显示考试时间、题量、注意事项）
2. 点击"开始考试" → 记录 started_at，启动倒计时
3. 答题界面：左侧材料区（可滚动），右侧作答区（逐题切换或全部展开）
4. 每题有独立的字数计数器，超字/少字实时提醒
5. 倒计时最后15分钟弹窗提醒
6. 提交或超时自动提交 → 批量调用 AI 批改 → 生成总分 + 各题分
7. 结果页展示：总分、各题得分、排名百分位、与上次对比
```

### 2.5 前端页面

**真题库页 `/papers`（升级现有页面）：**

```
┌─────────────────────────────────────────────────┐
│  筛选栏：[年份▼] [省份▼] [题型▼] [难度▼] [搜索]  │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐    │
│  │ 2024年国考·副省级  难度:★★★☆  1286人做过  │    │
│  │ 归纳概括 | 综合分析 | 贯彻执行 | 大作文      │    │
│  │ [逐题练习]  [全真模拟]  [查看解析]          │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │ 2024年国考·地市级  难度:★★★☆  986人做过   │    │
│  │ ...                                      │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

**模拟考场页 `/exam/simulate/<pid>`：**

```
┌─────────────────────────────────────────────────┐
│  2024国考副省级·全真模拟    ⏱ 剩余 02:15:30     │
├────────────────────────────┬────────────────────┤
│  材料区                     │  作答区             │
│  资料1                      │  第1题·归纳概括(15分)│
│  S市地处长三角腹地...        │  ┌──────────────┐  │
│  （可滚动浏览全部材料）       │  │              │  │
│                             │  │  字数: 0/200  │  │
│                             │  └──────────────┘  │
│                             │  [上一题] [下一题]  │
│                             │  ── 题目导航 ──     │
│                             │  [1✓] [2] [3] [4]  │
│                             │  [提交全部]         │
└────────────────────────────┴────────────────────┘
```

### 2.6 排名算法

```python
def calculate_rank_percentile(pid, user_score):
    """计算用户在同卷考生中的排名百分位"""
    scores = db.execute("""
        SELECT total_score FROM simulation_records
        WHERE pid = ? AND status = 'submitted'
        ORDER BY total_score
    """, (pid,)).fetchall()
    if not scores:
        return None
    below = sum(1 for s in scores if s['total_score'] < user_score)
    return round(below / len(scores) * 100, 1)
```

### 2.7 与闭环的衔接

- **输入**：备考计划指定本周模拟卷 → 推送到首页任务卡
- **输出**：模拟结果 → 各题得分写入 `user_question_type_stats` → 触发诊断报告更新 → 识别新的薄弱点

---

## 板块三：素材智能应用系统

### 3.1 设计目标

把现有的"好词好句库"从**被动浏览**升级为**主动应用**。解决"背了不会用"的核心痛点。

### 3.2 数据库变更

```sql
-- 升级 good_phrases 表，增加结构化字段
ALTER TABLE good_phrases ADD COLUMN category TEXT DEFAULT 'other';
-- category: jingji/shehui/wenhua/shengtai/minsheng/zhili/keji/other
ALTER TABLE good_phrases ADD COLUMN applicable_scenario TEXT;
-- 适用场景：开头引入/论据支撑/对策表述/结尾升华
ALTER TABLE good_phrases ADD COLUMN example_paragraph TEXT;
-- 示例段落：展示这句话在真实段落中怎么用
ALTER TABLE good_phrases ADD COLUMN difficulty INT DEFAULT 1;
-- 1基础/2进阶/3高级

-- 用户素材学习记录表（替代简单的收藏）
CREATE TABLE user_phrase_learning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    phrase_id INTEGER NOT NULL,
    mastery_level INT DEFAULT 0,    -- 0新学/1认识/2熟悉/3掌握
    next_review_at DATETIME,         -- 下次复习时间（间隔重复）
    review_count INT DEFAULT 0,
    last_reviewed_at DATETIME,
    applied_count INT DEFAULT 0,     -- 在作答中使用过的次数
    created_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (phrase_id) REFERENCES good_phrases(id),
    UNIQUE(uid, phrase_id)
);
CREATE INDEX idx_phrase_learn_uid ON user_phrase_learning(uid);
CREATE INDEX idx_phrase_learn_next ON user_phrase_learning(next_review_at);

-- 素材包表：按主题打包
CREATE TABLE phrase_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,             -- e.g. "乡村振兴素材包"
    description TEXT,
    theme TEXT NOT NULL,            -- 主题标签
    phrase_ids TEXT NOT NULL,       -- JSON: [1, 5, 12, 23]
    difficulty INT DEFAULT 1,
    sort_order INT DEFAULT 0,
    status TEXT DEFAULT 'published',
    created_at DATETIME DEFAULT datetime('now')
);
```

### 3.3 间隔重复算法

采用简化版 SM-2 算法：

```python
def calculate_next_review(mastery_level, review_count):
    """根据掌握程度计算下次复习时间"""
    intervals = {
        0: 1,       # 新学：1天后复习
        1: 3,       # 认识：3天后
        2: 7,       # 熟悉：7天后
        3: 30       # 掌握：30天后
    }
    days = intervals.get(mastery_level, 1)
    return datetime.now() + timedelta(days=days)
```

### 3.4 AI 造段功能

用户输入论点，AI 从素材库中匹配金句，生成示范段落：

```python
def generate_paragraph_with_phrases(user_point, theme, phrases_pool):
    """用素材库生成示范段落"""
    prompt = f"""
    你是申论写作专家。请围绕以下论点，写一个150字左右的申论段落。

    论点：{user_point}
    主题：{theme}

    请优先使用以下素材（金句）：
    {json.dumps(phrases_pool, ensure_ascii=False)}

    要求：
    1. 段落结构：论点句 → 分析/论据 → 回扣论点
    2. 至少嵌入2条素材，且嵌入自然不生硬
    3. 语言风格符合申论规范，避免口语化
    """
    return call_llm(prompt)
```

### 3.5 前端页面

**素材学习页 `/phrases/study`：**

```
┌─────────────────────────────────────────────────┐
│  今日待学：5条  已掌握：128条  总库存：356条      │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐    │
│  │ "治国之道，富民为始。"                     │    │
│  │ 来源：《人民日报》2024-03-15              │    │
│  │ 释义：治理国家的根本方法，在于让百姓富裕    │    │
│  │ 适用：民生保障、共同富裕主题               │    │
│  │ 示例段落：                               │    │
│  │ "治国之道，富民为始。共同富裕是社会主义的  │    │
│  │ 本质要求，必须通过制度安排......"          │    │
│  │                                          │    │
│  │ [不认识]  [认识]  [熟悉]  [掌握]          │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  ── 素材包推荐 ──                                │
│  [乡村振兴(28条)] [科技创新(22条)] [基层治理(31条)]│
└─────────────────────────────────────────────────┘
```

**AI 造段页 `/phrases/generate`：**

```
┌─────────────────────────────────────────────────┐
│  输入你的论点：                                   │
│  ┌─────────────────────────────────────────┐    │
│  │ 科技创新是推动高质量发展的第一动力         │    │
│  └─────────────────────────────────────────┘    │
│  主题：[科技创新▼]                               │
│  [生成示范段落]                                  │
│                                                 │
│  ── 生成结果 ──                                  │
│  ┌─────────────────────────────────────────┐    │
│  │ 科技创新是推动高质量发展的第一动力。       │    │
│  │ "关键核心技术是要不来、买不来、讨不来的"， │    │
│  │ 当前我国在芯片、基础软件等领域仍面临...... │    │
│  │ （使用了2条素材：第23条、第67条）          │    │
│  └─────────────────────────────────────────┘    │
│  [复制] [收藏段落] [换一批素材重新生成]           │
└─────────────────────────────────────────────────┘
```

### 3.6 与闭环的衔接

- **输入**：诊断报告"语言表达"维度得分低 → 推送对应主题素材包
- **输出**：用户在作答中使用素材 → `applied_count` 增加 → 素材掌握度提升 → 语言表达分提升

---

## 板块四：能力诊断报告系统

### 4.1 设计目标

这是**闭环的枢纽**。每次批改后不只是给一个分数，而是生成一份结构化的诊断报告，告诉用户：你哪里强、哪里弱、下一步练什么。

### 4.2 数据库变更

```sql
-- 诊断报告表
CREATE TABLE diagnostic_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    report_type TEXT NOT NULL,  -- single(单次)/weekly(周报)/monthly(月报)
    trigger_id TEXT,            -- 触发报告的 sid 或时间范围

    -- 五维度得分
    score_point_coverage REAL,  -- 踩点能力
    score_logic_structure REAL, -- 逻辑结构
    score_language REAL,        -- 语言表达
    score_format REAL,          -- 格式规范
    score_word_count REAL,      -- 字数控制

    -- 五题型得分
    score_guina REAL,
    score_zonghe REAL,
    score_duice REAL,
    score_zhixing REAL,
    score_zuowen REAL,

    -- 综合分析
    overall_score REAL,
    strengths TEXT,             -- JSON: ["踩点准确", "格式规范"]
    weaknesses TEXT,            -- JSON: ["逻辑链不完整", "语言口语化"]
    recommendations TEXT,       -- JSON: [{type, action, target_id, priority}]

    -- 趋势数据
    score_trend TEXT,           -- JSON: 近10次得分序列

    created_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid)
);
CREATE INDEX idx_diag_uid ON diagnostic_reports(uid);
CREATE INDEX idx_diag_type ON diagnostic_reports(report_type);
```

### 4.3 诊断算法

```python
def generate_diagnostic_report(uid, sid):
    """基于单次批改结果生成诊断报告"""
    submission = get_submission(sid)
    recent_submissions = get_recent_submissions(uid, limit=10)

    # 1. 五维度得分（直接从 dimension_scores 提取）
    dimensions = json.loads(submission['dimension_scores'])

    # 2. 五题型得分（从 user_question_type_stats 聚合）
    type_stats = get_user_type_stats(uid)

    # 3. 识别强弱项（与平台平均分对比）
    platform_avg = get_platform_averages(submission['pid'], submission['qid'])
    strengths = []
    weaknesses = []
    for dim, score in dimensions.items():
        avg = platform_avg.get(dim, 0)
        if score > avg * 1.15:
            strengths.append(dim)
        elif score < avg * 0.85:
            weaknesses.append(dim)

    # 4. 生成推荐
    recommendations = []
    for weakness in weaknesses:
        recommendations.append({
            'type': 'drill',
            'action': f'练习{weakness}相关的{get_weakest_type(uid)}题型',
            'target_id': get_recommended_paper(uid, weakness),
            'priority': 'high'
        })

    # 5. 趋势数据
    trend = [s['score'] for s in recent_submissions]

    return save_report(uid, dimensions, type_stats, strengths,
                       weaknesses, recommendations, trend)
```

### 4.4 前端页面

**诊断报告页 `/diagnosis/<report_id>`：**

```
┌─────────────────────────────────────────────────┐
│            你的申论能力诊断报告                    │
│            报告时间：2026-05-27                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─ 能力雷达图 ─┐   ┌─ 五题型得分 ─┐            │
│  │              │   │ 归纳概括  72  │            │
│  │    踩点      │   │ 综合分析  58  │            │
│  │   ╱    ╲     │   │ 提出对策  81  │            │
│  │  逻辑  语言   │   │ 贯彻执行  55  │            │
│  │  ╲    ╱      │   │ 大作文    68  │            │
│  │   格式       │   └──────────────┘            │
│  │   字数       │                                │
│  └──────────────┘                                │
│                                                 │
│  ── 趋势图（近10次）──                            │
│  85│         ·                                   │
│  75│    ·  ·   · ·                               │
│  65│  ·         ·  ·                             │
│  55│·                ·                           │
│   └──────────────────────                        │
│    1  2  3  4  5  6  7  8  9  10                │
│                                                 │
│  ── 你的优势 ──          ── 你的短板 ──           │
│  ✓ 踩点能力强(80分)      ✗ 逻辑结构弱(58分)      │
│  ✓ 格式规范(90分)        ✗ 贯彻执行题弱(55分)    │
│                                                 │
│  ── 下一步建议 ──                                │
│  1. [高] 本周重点练习综合分析题的逻辑链            │
│         → 推荐：2024国考副省级第2题               │
│         → [开始练习]                             │
│  2. [中] 背诵"基层治理"主题素材包(15条)           │
│         → [开始学习]                             │
│  3. [低] 贯彻执行题格式模板复习                   │
│         → [查看模板]                             │
└─────────────────────────────────────────────────┘
```

### 4.5 周报/月报

每周日晚自动生成周报，通过 Telegram Bot 推送：

```python
def generate_weekly_report(uid):
    """生成周报"""
    week_start = datetime.now() - timedelta(days=7)
    submissions = get_submissions_since(uid, week_start)

    if len(submissions) < 2:
        return None  # 数据太少不生成

    return {
        'type': 'weekly',
        'total_practices': len(submissions),
        'avg_score': mean([s['score'] for s in submissions]),
        'score_change': latest_avg - previous_week_avg,
        'best_type': max(type_stats, key=lambda t: t['avg_score']),
        'worst_type': min(type_stats, key=lambda t: t['avg_score']),
        'top_improvement': max(improvements, key=lambda i: i['delta']),
        'next_week_plan': generate_plan(uid, 'week')
    }
```

### 4.6 与闭环的衔接

- **输入**：每次批改完成后自动触发 → 生成单次诊断
- **输出**：推荐内容 → 推送到备考计划 → 驱动训练和素材学习

---

## 板块五：备考计划引擎

### 5.1 设计目标

解决用户"每天不知道练什么"的痛点。根据考试日期、当前水平、可用时间，自动生成个性化的每日任务。

### 5.2 数据库变更

```sql
-- 备考计划表
CREATE TABLE study_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    exam_date DATE NOT NULL,           -- 目标考试日期
    exam_type TEXT NOT NULL,           -- guokao/shengkao/xuandiao
    daily_minutes INT DEFAULT 120,     -- 每天可用学习时间
    current_level TEXT DEFAULT 'beginner',  -- beginner/intermediate/advanced

    -- 计划内容
    phases TEXT NOT NULL,              -- JSON: 分阶段计划
    daily_tasks TEXT NOT NULL,         -- JSON: 每日任务模板

    -- 状态
    status TEXT DEFAULT 'active',      -- active/completed/paused
    progress_pct REAL DEFAULT 0,       -- 完成进度
    streak_days INT DEFAULT 0,         -- 连续打卡天数
    longest_streak INT DEFAULT 0,      -- 最长连续天数

    created_at DATETIME DEFAULT datetime('now'),
    updated_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- 每日任务表
CREATE TABLE daily_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    plan_id INTEGER NOT NULL,
    task_date DATE NOT NULL,
    task_type TEXT NOT NULL,           -- drill/phrase_read/simulation/review/essay_write
    task_detail TEXT NOT NULL,         -- JSON: 具体任务描述
    target_id TEXT,                    -- 关联的 paper_id 或 phrase_pack_id
    status TEXT DEFAULT 'pending',     -- pending/in_progress/completed/skipped
    completed_at DATETIME,
    score REAL,                        -- 如果是练习，记录得分
    created_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (plan_id) REFERENCES study_plans(id)
);
CREATE INDEX idx_daily_uid_date ON daily_tasks(uid, task_date);
CREATE INDEX idx_daily_status ON daily_tasks(status);
```

### 5.3 计划生成算法

```python
def generate_study_plan(uid, exam_date, daily_minutes, exam_type):
    """根据用户参数生成备考计划"""
    days_remaining = (exam_date - date.today()).days
    current_level = assess_user_level(uid)  # 基于历史数据评估

    if days_remaining <= 0:
        raise ValueError("考试日期已过")

    # 分三个阶段
    if days_remaining > 60:
        phases = [
            {"name": "基础夯实", "days": int(days_remaining * 0.4),
             "focus": "分题型专项训练",
             "ratio": {"drill": 0.5, "phrase": 0.3, "essay": 0.2}},
            {"name": "强化提升", "days": int(days_remaining * 0.35),
             "focus": "全真模拟+薄弱项突破",
             "ratio": {"simulation": 0.4, "drill": 0.3, "phrase": 0.2, "review": 0.1}},
            {"name": "冲刺模考", "days": int(days_remaining * 0.25),
             "focus": "全真模考+素材巩固",
             "ratio": {"simulation": 0.5, "phrase": 0.3, "review": 0.2}}
        ]
    else:
        # 短期冲刺计划
        phases = [
            {"name": "重点突破", "days": int(days_remaining * 0.5),
             "focus": "薄弱题型+高频素材",
             "ratio": {"drill": 0.5, "phrase": 0.3, "simulation": 0.2}},
            {"name": "模考冲刺", "days": int(days_remaining * 0.5),
             "focus": "全真模考+查漏补缺",
             "ratio": {"simulation": 0.6, "review": 0.2, "phrase": 0.2}}
        ]

    # 生成每日任务
    daily_tasks = []
    for phase in phases:
        for day in range(phase['days']):
            task_date = date.today() + timedelta(days=len(daily_tasks))
            tasks = allocate_daily_tasks(uid, phase, daily_minutes, task_date)
            daily_tasks.extend(tasks)

    return save_plan(uid, exam_date, phases, daily_tasks)


def allocate_daily_tasks(uid, phase, minutes, task_date):
    """分配每日具体任务"""
    tasks = []
    remaining = minutes

    # 基于诊断报告的薄弱项优先分配
    weaknesses = get_user_weaknesses(uid)

    # 题型练习（最大的时间块）
    drill_minutes = int(minutes * phase['ratio'].get('drill', 0))
    if drill_minutes > 0:
        target_type = weaknesses[0] if weaknesses else 'guina'
        tasks.append({
            'task_type': 'drill',
            'task_detail': f'练习{get_type_name(target_type)}题 2道',
            'target_type': target_type,
            'estimated_minutes': drill_minutes,
            'task_date': task_date
        })
        remaining -= drill_minutes

    # 素材学习
    phrase_minutes = int(minutes * phase['ratio'].get('phrase', 0))
    if phrase_minutes > 0:
        # 推荐今天需要复习的素材（间隔重复）
        due_phrases = get_due_phrases(uid, limit=10)
        tasks.append({
            'task_type': 'phrase_read',
            'task_detail': f'学习/复习素材 {len(due_phrases)} 条',
            'estimated_minutes': phrase_minutes,
            'task_date': task_date
        })
        remaining -= phrase_minutes

    return tasks
```

### 5.4 前端页面

**备考计划首页 `/plan`：**

```
┌─────────────────────────────────────────────────┐
│  目标：2026年国考    距考试还有 47 天              │
│  备考进度：35%   连续打卡：12天                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ── 今日任务 ──                          0/3完成  │
│  ┌─────────────────────────────────────────┐    │
│  │ [ ] 归纳概括题练习 2道（约40分钟）        │    │
│  │   → 推荐：2024年山东省考第1题            │    │
│  │   [开始练习]                             │    │
│  ├─────────────────────────────────────────┤    │
│  │ [ ] 学习/复习素材 10条（约20分钟）        │    │
│  │   → "乡村振兴"主题素材包                 │    │
│  │   [开始学习]                             │    │
│  ├─────────────────────────────────────────┤    │
│  │ [ ] 大作文提纲练习 1篇（约60分钟）        │    │
│  │   → 主题：数字经济与实体经济融合           │    │
│  │   [开始练习]                             │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  ── 本周进度 ──                                  │
│  一  二  三  四  五  六  日                       │
│  ✓   ✓   ✓   ●   ·   ·   ·                     │
│  (完成  进行中  未到)                             │
│                                                 │
│  ── 阶段：基础夯实(第3周/共6周) ──                │
│  ████████████░░░░░░░░░░ 50%                     │
│  重点：归纳概括 + 综合分析                        │
└─────────────────────────────────────────────────┘
```

**任务完成后的即时反馈：**

```
┌─────────────────────────────────────────────────┐
│  今日任务完成！                                   │
│                                                 │
│  归纳概括：78分（↑5 vs 上次）                     │
│  素材学习：掌握8条，复习2条                       │
│                                                 │
│  连续打卡：13天                                  │
│  本周均分：74.2（上周 71.5）                      │
│                                                 │
│  明日预告：综合分析题练习 + 基层治理素材           │
└─────────────────────────────────────────────────┘
```

### 5.5 与闭环的衔接

- **输入**：诊断报告的薄弱项 → 影响每日任务分配的优先级
- **输出**：每日任务完成情况 → 更新学习记录 → 影响诊断报告 → 调整后续计划

---

## 板块六：时政热点专题

### 6.1 设计目标

申论材料越来越贴近时政。用户需要系统性的热点积累，而不是碎片化的新闻浏览。

### 6.2 数据库变更

```sql
-- 热点专题表
CREATE TABLE hot_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,              -- e.g. "新质生产力"
    summary TEXT NOT NULL,            -- 300字以内的背景梳理
    category TEXT NOT NULL,           -- jingji/shehui/wenhua/shengtai/minsheng/zhili/keji
    keywords TEXT DEFAULT '[]',       -- JSON: 关键词列表
    multi_views TEXT,                 -- JSON: 多方观点
    related_phrases TEXT DEFAULT '[]', -- JSON: 关联素材ID
    related_papers TEXT DEFAULT '[]', -- JSON: 关联真题ID
    exam_prediction TEXT,             -- AI押题分析
    exam_history TEXT DEFAULT '[]',   -- JSON: 历年考过的相关题目
    week_label TEXT,                  -- e.g. "2026-W22"
    status TEXT DEFAULT 'published',
    created_at DATETIME DEFAULT datetime('now')
);

-- 用户热点学习记录
CREATE TABLE user_topic_learning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    is_read INTEGER DEFAULT 0,
    is_bookmarked INTEGER DEFAULT 0,
    notes TEXT,                       -- 用户自己的笔记
    created_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (topic_id) REFERENCES hot_topics(id),
    UNIQUE(uid, topic_id)
);
```

### 6.3 热点内容结构

每个热点专题的标准结构：

```json
{
  "title": "新质生产力",
  "summary": "2024年9月，习近平总书记在黑龙江考察时首次提出...",
  "category": "jingji",
  "keywords": ["新质生产力", "科技创新", "产业升级", "数字经济"],
  "multi_views": [
    {"perspective": "经济学者", "view": "新质生产力的核心是全要素生产率的提升..."},
    {"perspective": "产业界", "view": "关键在于打通科技成果转化的最后一公里..."},
    {"perspective": "基层实践", "view": "传统产业的数字化转型是新质生产力的重要载体..."}
  ],
  "related_phrases": [23, 45, 67, 89],
  "exam_prediction": {
    "possible_angles": [
      "如何理解'新质生产力'与'高质量发展'的关系",
      "地方政府如何因地制宜发展新质生产力"
    ],
    "probability": "high",
    "reason": "连续两年政府工作报告重点提及，2025年省考多省涉及"
  },
  "exam_history": [
    {"year": 2025, "exam": "浙江省考", "question": "分析数字经济对传统产业转型升级的作用"},
    {"year": 2024, "exam": "国考副省", "question": "概括科技创新推动高质量发展的做法"}
  ]
}
```

### 6.4 AI 热点押题

```python
def predict_exam_topics():
    """基于历年真题和政策趋势，预测考试热点"""
    # 1. 分析近5年真题的高频主题
    topic_frequency = analyze_topic_frequency(years=5)

    # 2. 获取近3个月的重大政策/讲话
    recent_policies = crawl_recent_policies(months=3)

    # 3. 交叉分析
    prompt = f"""
    你是申论命题研究专家。

    近5年申论高频主题：{json.dumps(topic_frequency)}
    近3个月重大政策：{json.dumps(recent_policies)}

    请预测未来半年最可能考的5个方向，每个方向给出：
    1. 主题名称
    2. 可能的出题角度
    3. 概率评估（高/中/低）
    4. 理由
    """
    return call_llm(prompt)
```

### 6.5 前端页面

**热点专题页 `/topics`：**

```
┌─────────────────────────────────────────────────┐
│  时政热点专题                     [本周] [往期▼]  │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐    │
│  │ 本周热点  2026年第22周                    │    │
│  ├─────────────────────────────────────────┤    │
│  │ 1. 低空经济与新质生产力       [已读]      │    │
│  │    考试概率：高   关联真题：3道           │    │
│  │ 2. 基层治理现代化             [未读]      │    │
│  │    考试概率：高   关联真题：5道           │    │
│  │ 3. 数字政府建设               [未读]      │    │
│  │    考试概率：中   关联真题：2道           │    │
│  └─────────────────────────────────────────┘    │
│                                                 │
│  ── AI押题预测 ──                                │
│  ┌─────────────────────────────────────────┐    │
│  │ 预测2026国考最可能考的3个方向：            │    │
│  │ 1. 新质生产力与产业升级（概率：高）        │    │
│  │ 2. 基层社会治理创新（概率：高）            │    │
│  │ 3. 乡村振兴与共同富裕（概率：中）          │    │
│  │ [查看详情]  [下载押题素材包]               │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### 6.6 与闭环的衔接

- **输入**：用户目标考试类型 → 推荐对应省份/级别的热点
- **输出**：热点关联素材 → 自动加入素材学习队列；热点关联真题 → 自动加入练习队列

---

## 板块七：社区互助系统

### 7.1 设计目标

增加用户粘性和内容生态。让用户互相点评、分享优秀答案、形成学习氛围。

### 7.2 数据库变更

```sql
-- 社区帖子表
CREATE TABLE community_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    post_type TEXT NOT NULL,     -- answer_share/question/discussion/tips
    title TEXT,
    content TEXT NOT NULL,

    -- 关联信息
    related_sid TEXT,            -- 如果是晒答案，关联 submission
    related_pid TEXT,
    related_qid TEXT,

    -- 互动数据
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,

    -- 管理
    is_featured INTEGER DEFAULT 0,  -- 精选
    is_pinned INTEGER DEFAULT 0,    -- 置顶
    status TEXT DEFAULT 'published',

    created_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- 评论表
CREATE TABLE community_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    uid TEXT NOT NULL,
    content TEXT NOT NULL,
    parent_comment_id INTEGER,   -- 回复某条评论
    like_count INT DEFAULT 0,
    status TEXT DEFAULT 'published',
    created_at DATETIME DEFAULT datetime('now'),
    FOREIGN KEY (post_id) REFERENCES community_posts(id),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- 点赞表
CREATE TABLE community_likes (
    uid TEXT NOT NULL,
    target_type TEXT NOT NULL,   -- post/comment
    target_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT datetime('now'),
    PRIMARY KEY (uid, target_type, target_id)
);
```

### 7.3 核心功能

**晒答案 + AI 辅助点评：**
用户可以把自己的答案分享到社区，其他人可以看到 AI 批改结果并补充自己的点评。

**范文精选：**
管理员可以将社区中的优秀答案标记为"范文"，附上 AI 点评和人工点评，形成 UGC 内容。

**求助帖：**
用户贴出自己的困惑（"这道题我怎么都写不好"），社区高手可以回复指导。

### 7.4 前端页面

**社区首页 `/community`：**

```
┌─────────────────────────────────────────────────┐
│  [全部] [晒答案] [求助] [讨论] [备考经验]         │
├─────────────────────────────────────────────────┤
│  精选范文：2024国考归纳概括满分答案赏析            │
│     -- by 上岸的鱼 · 286赞 · 45评论              │
├─────────────────────────────────────────────────┤
│                                                 │
│  最新帖子                                        │
│  ┌─────────────────────────────────────────┐    │
│  │ [晒答案] 2024山东省考第2题 我得了82分！    │    │
│  │ AI评语：踩点完整，逻辑清晰，建议...        │    │
│  │ by 努力上岸中 · 12赞 · 3评论 · 2小时前    │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │ [求助] 综合分析题的逻辑链怎么练？          │    │
│  │ 每次写综合分析都被说逻辑不完整...          │    │
│  │ by 考公小白 · 8赞 · 15评论 · 5小时前     │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### 7.5 与闭环的衔接

- **输入**：诊断报告中的薄弱项 → 推荐相关社区帖子/范文
- **输出**：社区互动数据 → 识别高质量用户 → 邀请成为"导师"角色

---

## 全生命周期数据流转图

```
┌──────────────────────────────────────────────────────────────┐
│                        用户生命周期                            │
│                                                              │
│  新用户                                                       │
│    ↓                                                         │
│  [注册] → [首次诊断测试] → 生成初始能力画像                     │
│    ↓                                                         │
│  [创建备考计划] ← 根据考试日期 + 能力画像自动生成                │
│    ↓                                                         │
│  ┌─ 每日循环 ──────────────────────────────────────────────┐  │
│  │                                                         │  │
│  │  ① 查看今日任务                                          │  │
│  │     ↓                                                   │  │
│  │  ② 题型训练 / 全真模拟                                   │  │
│  │     ↓                                                   │  │
│  │  ③ AI批改 → 诊断报告更新                                 │  │
│  │     ↓                                                   │  │
│  │  ④ 薄弱点识别 → 自动调整明日任务                          │  │
│  │     ↓                                                   │  │
│  │  ⑤ 素材学习（间隔重复）                                   │  │
│  │     ↓                                                   │  │
│  │  ⑥ 打卡 → 连续天数 +1                                    │  │
│  │     ↓                                                   │  │
│  │  ⑦ 周末：时政热点学习                                     │  │
│  │     ↓                                                   │  │
│  │  ⑧ 可选：社区互动                                        │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│    ↓                                                         │
│  [周报生成] → Telegram推送 → 用户查看进步趋势                   │
│    ↓                                                         │
│  [考前冲刺] → 加大模考频率 → 押题素材包推送                     │
│    ↓                                                         │
│  [考试]                                                      │
│    ↓                                                         │
│  [上岸！] → 社区分享经验 → 引流新用户                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 实施优先级与排期

| 阶段 | 板块 | 工作量 | 核心产出 |
|------|------|--------|----------|
| **Phase 1** (2周) | 题型专项训练 + 能力诊断 | 大 | 5套独立 Prompt、题型统计表、诊断报告页 |
| **Phase 2** (1.5周) | 真题库升级 + 模拟考场 | 中 | 倒计时答题 UI、排名系统、真题筛选 |
| **Phase 3** (1.5周) | 素材应用系统 | 中 | 间隔重复、AI 造段、素材包 |
| **Phase 4** (1周) | 备考计划引擎 | 中 | 计划生成算法、每日任务页 |
| **Phase 5** (1周) | 时政热点专题 | 小 | 热点内容结构、AI 押题 |
| **Phase 6** (1周) | 社区系统 | 小 | 晒答案、评论、范文精选 |

**总计约 8 周**，每个阶段完成后都可独立上线，用户立即获得价值。

---

## 新增数据库表汇总

| 表名 | 所属板块 | 用途 |
|------|----------|------|
| `user_question_type_stats` | 板块一 | 用户五题型能力画像 |
| `question_type_drills` | 板块一 | 题型训练记录 |
| `simulation_records` | 板块二 | 模拟考试记录 |
| `user_phrase_learning` | 板块三 | 素材学习进度（间隔重复） |
| `phrase_packs` | 板块三 | 主题素材包 |
| `diagnostic_reports` | 板块四 | 能力诊断报告 |
| `study_plans` | 板块五 | 备考计划 |
| `daily_tasks` | 板块五 | 每日任务 |
| `hot_topics` | 板块六 | 时政热点专题 |
| `user_topic_learning` | 板块六 | 用户热点学习记录 |
| `community_posts` | 板块七 | 社区帖子 |
| `community_comments` | 板块七 | 社区评论 |
| `community_likes` | 板块七 | 点赞记录 |

## 新增 API 端点汇总

```
板块一：题型训练
  GET  /api/drill/types
  GET  /api/drill/recommend?type=guina
  POST /api/drill/submit
  GET  /api/drill/history?type=guina&page=1
  GET  /api/drill/progress?type=guina

板块二：模拟考场
  POST /api/simulation/start
  POST /api/simulation/submit
  GET  /api/simulation/rank/<pid>
  GET  /api/simulation/history

板块三：素材系统
  GET  /api/phrases/study/today
  POST /api/phrases/study/review
  GET  /api/phrases/packs
  POST /api/phrases/generate

板块四：诊断报告
  GET  /api/diagnosis/latest
  GET  /api/diagnosis/<report_id>
  GET  /api/diagnosis/trend
  GET  /api/diagnosis/weekly

板块五：备考计划
  POST /api/plan/create
  GET  /api/plan/current
  GET  /api/plan/tasks/today
  POST /api/plan/tasks/<task_id>/complete

板块六：热点专题
  GET  /api/topics/weekly
  GET  /api/topics/<topic_id>
  POST /api/topics/<topic_id>/bookmark
  GET  /api/topics/predict

板块七：社区
  GET  /api/community/posts
  POST /api/community/posts
  POST /api/community/posts/<id>/like
  POST /api/community/posts/<id>/comment
```

## 新增前端页面汇总

```
/drill                    -- 题型训练选择页
/drill/<type>             -- 单题型训练页
/papers                   -- 真题库（升级）
/exam/simulate/<pid>      -- 全真模拟考场
/phrases/study            -- 素材学习页
/phrases/generate         -- AI 造段页
/diagnosis                -- 诊断报告列表
/diagnosis/<report_id>    -- 单份诊断报告
/plan                     -- 备考计划首页
/topics                   -- 时政热点专题
/community                -- 社区首页
```
