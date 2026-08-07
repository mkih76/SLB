-- SLB 申论AI批改平台 数据库Schema
-- 执行顺序: 依次执行所有CREATE TABLE语句

-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    uid           TEXT PRIMARY KEY,          -- UUID
    username      TEXT UNIQUE NOT NULL,      -- 登录用户名
    password_hash TEXT NOT NULL,              -- bcrypt 哈希
    nickname      TEXT,                      -- 显示昵称
    avatar_url    TEXT,                      -- 头像URL
    role          TEXT DEFAULT 'user',       -- user / admin / vip
    phone         TEXT,                      -- 手机号（可选）
    email         TEXT,                      -- 邮箱（可选）
    vip_expire    DATETIME,                  -- VIP过期时间
    free_trial_used INT DEFAULT 0,           -- 免费试用是否已使用
    created_at    DATETIME DEFAULT (datetime('now')),
    last_login    DATETIME,
    status        TEXT DEFAULT 'active',     -- active / banned
    settings      TEXT DEFAULT '{}'          -- JSON偏好设置
);

-- ============================================================
-- 会话表
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    sid        TEXT PRIMARY KEY,
    uid        TEXT NOT NULL,
    token      TEXT UNIQUE NOT NULL,
    ip         TEXT,
    user_agent TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    expires_at DATETIME NOT NULL,
    FOREIGN KEY (uid) REFERENCES users(uid)
);

CREATE INDEX IF NOT EXISTS idx_sessions_uid ON sessions(uid);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);

-- ============================================================
-- 试卷表
-- ============================================================
CREATE TABLE IF NOT EXISTS papers (
    pid           TEXT PRIMARY KEY,          -- fb_2024gwy_sl_001
    source        TEXT NOT NULL,             -- 粉笔 / 中公 / 华图 / 自建
    exam_type     TEXT NOT NULL,             -- 国考 / 省考 / 事业单位
    year          INT NOT NULL,
    season        TEXT,                      -- 省级 / 地市级
    province      TEXT,                      -- 浙江 / 江苏 / null（国考）
    title         TEXT NOT NULL,
    material      TEXT NOT NULL,             -- JSON数组（分段材料）
    questions     TEXT NOT NULL,            -- JSON数组（题目+答案要点）
    answer_keys   TEXT NOT NULL,            -- JSON（标准答案要点）
    difficulty    INT DEFAULT 3,            -- 1-5
    heat          INT DEFAULT 0,            -- 热度/使用次数
    tag           TEXT DEFAULT '[]',         -- JSON标签
    source_url    TEXT,                      -- 原始链接
    status        TEXT DEFAULT 'published',  -- draft / published / archived
    created_at    DATETIME DEFAULT (datetime('now')),
    crawled_at    DATETIME
);

CREATE INDEX IF NOT EXISTS idx_papers_exam_type ON papers(exam_type);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_province ON papers(province);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);

-- ============================================================
-- 提交记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS submissions (
    sid                TEXT PRIMARY KEY,
    uid                TEXT NOT NULL,
    pid                TEXT NOT NULL,
    qid                TEXT NOT NULL,
    user_answer        TEXT NOT NULL,
    score              REAL,                  -- 总分（NULL=未批改）
    dimension_scores   TEXT,                  -- JSON各维度得分
    ai_feedback        TEXT,                  -- AI详细批注
    hit_points         TEXT DEFAULT '[]',     -- JSON命中的关键词
    missing_points     TEXT DEFAULT '[]',     -- JSON遗漏的关键词
    improving_suggestions TEXT,              -- AI改进建议
    graded_at          DATETIME,
    is_reviewed        INT DEFAULT 0,         -- 用户是否查看
    needs_review       INT DEFAULT 0,         -- 是否需要人工复核
    reviewer_uid       TEXT,                  -- 复核人uid
    share_token        TEXT,                  -- 分享链接token
    share_expires_at   DATETIME,             -- 分享链接过期时间（30天）
    created_at         DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (pid) REFERENCES papers(pid)
);

CREATE INDEX IF NOT EXISTS idx_submissions_uid ON submissions(uid);
CREATE INDEX IF NOT EXISTS idx_submissions_pid ON submissions(pid);
CREATE INDEX IF NOT EXISTS idx_submissions_created ON submissions(created_at);
CREATE INDEX IF NOT EXISTS idx_submissions_score ON submissions(score);
CREATE INDEX IF NOT EXISTS idx_submissions_review ON submissions(is_reviewed, needs_review, score);

-- ============================================================
-- 薄弱点表
-- ============================================================
CREATE TABLE IF NOT EXISTS weak_points (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uid           TEXT NOT NULL,
    pid           TEXT,
    qid           TEXT,
    missing_key   TEXT NOT NULL,             -- 遗漏的采分点关键词
    topic_tag     TEXT,                      -- 归类标签：乡村振兴/基层治理
    times_missed  INT DEFAULT 1,              -- 被遗漏次数
    review_count  INT DEFAULT 0,              -- 复习次数
    last_reviewed DATETIME,
    created_at    DATETIME DEFAULT (datetime('now')),
    UNIQUE(uid, missing_key)
);

CREATE INDEX IF NOT EXISTS idx_weak_uid ON weak_points(uid);
CREATE INDEX IF NOT EXISTS idx_weak_topic ON weak_points(topic_tag);

-- ============================================================
-- 好词好句表
-- ============================================================
CREATE TABLE IF NOT EXISTS good_phrases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    phrase        TEXT NOT NULL,             -- 好词好句原文
    translation   TEXT,                       -- 解读/翻译
    usage         TEXT,                       -- 用法/适用场景
    source        TEXT NOT NULL,              -- 来源：人民日报 / 求是 / 新华网
    source_url    TEXT,                       -- 原文链接
    source_date   DATE,                       -- 发表日期
    tag           TEXT DEFAULT '[]',          -- JSON标签
    heat          INT DEFAULT 0,              -- 使用热度
    status        TEXT DEFAULT 'pending',    -- pending / approved / rejected
    approved_by   TEXT,                       -- 审核人uid
    created_at    DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_phrases_status ON good_phrases(status);
CREATE INDEX IF NOT EXISTS idx_phrases_source ON good_phrases(source);

-- ============================================================
-- 好词收藏表
-- ============================================================
CREATE TABLE IF NOT EXISTS user_favorites (
    uid           TEXT NOT NULL,
    phrase_id     INTEGER NOT NULL,
    note          TEXT,                       -- 用户笔记
    created_at    DATETIME DEFAULT (datetime('now')),
    PRIMARY KEY (uid, phrase_id),
    FOREIGN KEY (phrase_id) REFERENCES good_phrases(id)
);

-- ============================================================
-- 学习记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS learning_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uid           TEXT NOT NULL,
    action        TEXT NOT NULL,              -- submit / review / favorite / weak_review
    target_id     TEXT NOT NULL,             -- submission_id / phrase_id / weak_id
    score         REAL,                       -- 若为submit则记录得分
    created_at    DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_records_uid ON learning_records(uid);
CREATE INDEX IF NOT EXISTS idx_records_action ON learning_records(action);
CREATE INDEX IF NOT EXISTS idx_records_created ON learning_records(created_at);

-- ============================================================
-- 管理员操作日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS admin_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_uid     TEXT NOT NULL,
    action        TEXT NOT NULL,              -- approve_phrase / delete_paper / ban_user
    target_type   TEXT,                       -- paper / user / phrase
    target_id     TEXT,
    detail        TEXT,                       -- 操作详情JSON
    created_at    DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_admin_logs_admin ON admin_logs(admin_uid);
CREATE INDEX IF NOT EXISTS idx_admin_logs_action ON admin_logs(action);
CREATE INDEX IF NOT EXISTS idx_admin_logs_created ON admin_logs(created_at);

-- ============================================================
-- Token黑名单表（JWT登出支持）
-- ============================================================
CREATE TABLE IF NOT EXISTS token_blacklist (
    jti           TEXT PRIMARY KEY,              -- JWT ID
    uid           TEXT NOT NULL,
    expires_at    DATETIME NOT NULL,
    created_at    DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_blacklist_uid ON token_blacklist(uid);
CREATE INDEX IF NOT EXISTS idx_blacklist_expires ON token_blacklist(expires_at);

-- ============================================================
-- 题型能力画像表（板块一）
-- ============================================================
CREATE TABLE IF NOT EXISTS user_question_type_stats (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    uid                TEXT NOT NULL,
    question_type      TEXT NOT NULL,          -- guina/zonghe/duice/zhixing/zuowen
    total_attempts     INT DEFAULT 0,
    total_score        REAL DEFAULT 0,
    avg_score          REAL DEFAULT 0,
    best_score         REAL DEFAULT 0,
    last_attempt_at    DATETIME,
    dimension_breakdown TEXT DEFAULT '{}',     -- JSON: 各维度平均分
    level              TEXT DEFAULT 'bronze',  -- bronze/silver/gold/platinum/diamond
    created_at         DATETIME DEFAULT (datetime('now')),
    updated_at         DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    UNIQUE(uid, question_type)
);

CREATE INDEX IF NOT EXISTS idx_uqts_uid ON user_question_type_stats(uid);

-- ============================================================
-- 题型训练记录表（板块一）
-- ============================================================
CREATE TABLE IF NOT EXISTS question_type_drills (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    uid                TEXT NOT NULL,
    question_type      TEXT NOT NULL,
    pid                TEXT NOT NULL,
    qid                TEXT NOT NULL,
    sid                TEXT,                   -- 关联 submissions 表
    score              REAL,
    dimension_scores   TEXT,                   -- JSON
    key_point_hit_rate REAL,                   -- 踩点率
    time_spent         INT,                    -- 用时（秒）
    created_at         DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (pid) REFERENCES papers(pid)
);

CREATE INDEX IF NOT EXISTS idx_drills_uid_type ON question_type_drills(uid, question_type);

-- ============================================================
-- 诊断报告表（板块四）
-- ============================================================
CREATE TABLE IF NOT EXISTS diagnostic_reports (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    uid                   TEXT NOT NULL,
    report_type           TEXT NOT NULL,       -- single/weekly/monthly
    trigger_id            TEXT,                -- 触发报告的 sid

    -- 五维度得分
    score_point_coverage  REAL,
    score_logic_structure REAL,
    score_language        REAL,
    score_format          REAL,
    score_word_count      REAL,

    -- 五题型得分
    score_guina           REAL,
    score_zonghe          REAL,
    score_duice           REAL,
    score_zhixing         REAL,
    score_zuowen          REAL,

    -- 综合分析
    overall_score         REAL,
    strengths             TEXT,                -- JSON
    weaknesses            TEXT,                -- JSON
    recommendations       TEXT,                -- JSON
    score_trend           TEXT,                -- JSON: 近10次得分序列

    created_at            DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

CREATE INDEX IF NOT EXISTS idx_diag_uid ON diagnostic_reports(uid);
CREATE INDEX IF NOT EXISTS idx_diag_type ON diagnostic_reports(report_type);

-- ============================================================
-- 模拟考试记录表（板块二）
-- ============================================================
CREATE TABLE IF NOT EXISTS simulation_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    uid              TEXT NOT NULL,
    pid              TEXT NOT NULL,
    started_at       DATETIME NOT NULL,
    submitted_at     DATETIME,
    time_spent       INT,                     -- 实际用时（秒）
    total_score      REAL,
    question_scores  TEXT,                     -- JSON
    rank_percentile  REAL,
    status           TEXT DEFAULT 'in_progress', -- in_progress/submitted/timeout
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (pid) REFERENCES papers(pid)
);

CREATE INDEX IF NOT EXISTS idx_sim_uid ON simulation_records(uid);
CREATE INDEX IF NOT EXISTS idx_sim_pid ON simulation_records(pid);

-- ============================================================
-- 素材学习记录表（板块三）
-- ============================================================
CREATE TABLE IF NOT EXISTS user_phrase_learning (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    phrase_id       INTEGER NOT NULL,
    mastery_level   INT DEFAULT 0,              -- 0新学/1认识/2熟悉/3掌握
    next_review_at  DATETIME,                   -- 下次复习时间（间隔重复）
    review_count    INT DEFAULT 0,
    last_reviewed_at DATETIME,
    applied_count   INT DEFAULT 0,              -- 在作答中使用过的次数
    created_at      DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (phrase_id) REFERENCES good_phrases(id),
    UNIQUE(uid, phrase_id)
);

CREATE INDEX IF NOT EXISTS idx_phrase_learn_uid ON user_phrase_learning(uid);
CREATE INDEX IF NOT EXISTS idx_phrase_learn_next ON user_phrase_learning(next_review_at);

-- ============================================================
-- 素材包表（板块三）
-- ============================================================
CREATE TABLE IF NOT EXISTS phrase_packs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,              -- e.g. "乡村振兴素材包"
    description     TEXT,
    theme           TEXT NOT NULL,              -- 主题标签
    phrase_ids      TEXT NOT NULL,              -- JSON: [1, 5, 12, 23]
    difficulty      INT DEFAULT 1,              -- 1基础/2进阶/3高级
    sort_order      INT DEFAULT 0,
    status          TEXT DEFAULT 'published',
    created_at      DATETIME DEFAULT (datetime('now'))
);

-- ============================================================
-- 备考计划表（板块五）
-- ============================================================
CREATE TABLE IF NOT EXISTS study_plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    plan_name       TEXT NOT NULL,
    exam_date       DATE NOT NULL,              -- 目标考试日期
    exam_type       TEXT NOT NULL,              -- guokao/shengkao/xuandiao
    daily_minutes   INT DEFAULT 120,            -- 每天可用学习时间
    current_level   TEXT DEFAULT 'beginner',    -- beginner/intermediate/advanced
    phases          TEXT NOT NULL,              -- JSON: 分阶段计划
    daily_tasks_tmpl TEXT NOT NULL,             -- JSON: 每日任务模板
    status          TEXT DEFAULT 'active',      -- active/completed/paused
    progress_pct    REAL DEFAULT 0,             -- 完成进度
    streak_days     INT DEFAULT 0,              -- 连续打卡天数
    longest_streak  INT DEFAULT 0,              -- 最长连续天数
    created_at      DATETIME DEFAULT (datetime('now')),
    updated_at      DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

CREATE INDEX IF NOT EXISTS idx_plan_uid ON study_plans(uid);

-- ============================================================
-- 每日任务表（板块五）
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    plan_id         INTEGER NOT NULL,
    task_date       DATE NOT NULL,
    task_type       TEXT NOT NULL,              -- drill/phrase_read/simulation/review/essay_write
    task_detail     TEXT NOT NULL,              -- JSON: 具体任务描述
    target_id       TEXT,                       -- 关联的 paper_id 或 phrase_pack_id
    status          TEXT DEFAULT 'pending',     -- pending/in_progress/completed/skipped
    completed_at    DATETIME,
    score           REAL,                       -- 如果是练习，记录得分
    created_at      DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (plan_id) REFERENCES study_plans(id)
);

CREATE INDEX IF NOT EXISTS idx_daily_uid_date ON daily_tasks(uid, task_date);
CREATE INDEX IF NOT EXISTS idx_daily_status ON daily_tasks(status);

-- ============================================================
-- 热点专题表（板块六）
-- ============================================================
CREATE TABLE IF NOT EXISTS hot_topics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,              -- e.g. "新质生产力"
    summary         TEXT NOT NULL,              -- 300字以内的背景梳理
    category        TEXT NOT NULL,              -- jingji/shehui/wenhua/shengtai/minsheng/zhili/keji
    keywords        TEXT DEFAULT '[]',          -- JSON: 关键词列表
    multi_views     TEXT,                       -- JSON: 多方观点
    related_phrases TEXT DEFAULT '[]',          -- JSON: 关联素材ID
    related_papers  TEXT DEFAULT '[]',          -- JSON: 关联真题ID
    exam_prediction TEXT,                       -- JSON: AI押题分析
    exam_history    TEXT DEFAULT '[]',          -- JSON: 历年考过的相关题目
    week_label      TEXT,                       -- e.g. "2026-W22"
    status          TEXT DEFAULT 'published',
    created_at      DATETIME DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_topic_status ON hot_topics(status);
CREATE INDEX IF NOT EXISTS idx_topic_week ON hot_topics(week_label);
CREATE INDEX IF NOT EXISTS idx_topic_category ON hot_topics(category);

-- ============================================================
-- 用户热点学习记录（板块六）
-- ============================================================
CREATE TABLE IF NOT EXISTS user_topic_learning (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    topic_id        INTEGER NOT NULL,
    is_read         INTEGER DEFAULT 0,
    is_bookmarked   INTEGER DEFAULT 0,
    notes           TEXT,                       -- 用户自己的笔记
    created_at      DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (topic_id) REFERENCES hot_topics(id),
    UNIQUE(uid, topic_id)
);

CREATE INDEX IF NOT EXISTS idx_topic_learn_uid ON user_topic_learning(uid);

-- ============================================================
-- 社区帖子表（板块七）
-- ============================================================
CREATE TABLE IF NOT EXISTS community_posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    post_type       TEXT NOT NULL,              -- answer_share/question/discussion/tips
    title           TEXT,
    content         TEXT NOT NULL,
    related_sid     TEXT,                       -- 如果是晒答案，关联 submission
    related_pid     TEXT,
    related_qid     TEXT,
    view_count      INT DEFAULT 0,
    like_count      INT DEFAULT 0,
    comment_count   INT DEFAULT 0,
    is_featured     INTEGER DEFAULT 0,          -- 精选
    is_pinned       INTEGER DEFAULT 0,          -- 置顶
    status          TEXT DEFAULT 'published',
    created_at      DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

CREATE INDEX IF NOT EXISTS idx_post_uid ON community_posts(uid);
CREATE INDEX IF NOT EXISTS idx_post_type ON community_posts(post_type);
CREATE INDEX IF NOT EXISTS idx_post_status ON community_posts(status);

-- ============================================================
-- 社区评论表（板块七）
-- ============================================================
CREATE TABLE IF NOT EXISTS community_comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER NOT NULL,
    uid             TEXT NOT NULL,
    content         TEXT NOT NULL,
    parent_comment_id INTEGER,                  -- 回复某条评论
    like_count      INT DEFAULT 0,
    status          TEXT DEFAULT 'published',
    created_at      DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (post_id) REFERENCES community_posts(id),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

CREATE INDEX IF NOT EXISTS idx_comment_post ON community_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_comment_uid ON community_comments(uid);

-- ============================================================
-- 社区点赞表（板块七）
-- ============================================================
CREATE TABLE IF NOT EXISTS community_likes (
    uid             TEXT NOT NULL,
    target_type     TEXT NOT NULL,              -- post/comment
    target_id       INTEGER NOT NULL,
    created_at      DATETIME DEFAULT (datetime('now')),
    PRIMARY KEY (uid, target_type, target_id)
);

-- ============================================================
-- 系统设置表
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    key           TEXT PRIMARY KEY,
    value         TEXT NOT NULL,
    updated_at    DATETIME DEFAULT (datetime('now'))
);

-- ============================================================
-- 签到记录表（用户增长）
-- ============================================================
CREATE TABLE IF NOT EXISTS sign_in_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uid           TEXT NOT NULL,
    sign_date     DATE NOT NULL,
    streak_days   INT DEFAULT 1,              -- 连续签到天数
    reward_points INT DEFAULT 0,              -- 奖励积分
    created_at    DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    UNIQUE(uid, sign_date)
);

CREATE INDEX IF NOT EXISTS idx_signin_uid ON sign_in_records(uid);
CREATE INDEX IF NOT EXISTS idx_signin_date ON sign_in_records(sign_date);

-- ============================================================
-- 用户积分表（用户增长）
-- ============================================================
CREATE TABLE IF NOT EXISTS user_points (
    uid           TEXT PRIMARY KEY,
    total_points  INT DEFAULT 0,
    used_points   INT DEFAULT 0,
    updated_at    DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- ============================================================
-- 管理员账号（默认）
-- ============================================================
-- 密码: admin123456 (bcrypt hash)
-- 建议部署后立即修改默认密码
INSERT OR IGNORE INTO users (uid, username, password_hash, nickname, role, status)
VALUES (
    'admin_001',
    'admin',
    '$2b$12$3SgOuIxbtK.A.qTcM3vbq.7nbqoEUJqvf6LkeBX.g8oLWw2ZOpQR2',
    '管理员',
    'admin',
    'active'
);
