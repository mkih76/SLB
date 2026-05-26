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
    created_at         DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (pid) REFERENCES papers(pid)
);

CREATE INDEX IF NOT EXISTS idx_submissions_uid ON submissions(uid);
CREATE INDEX IF NOT EXISTS idx_submissions_pid ON submissions(pid);
CREATE INDEX IF NOT EXISTS idx_submissions_created ON submissions(created_at);

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

-- ============================================================
-- 管理员账号（默认）
-- ============================================================
-- 密码: admin123456 (bcrypt hash)
-- 建议部署后立即修改默认密码
INSERT OR IGNORE INTO users (uid, username, password_hash, nickname, role, status)
VALUES (
    'admin_001',
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiAYxMHHO3Oq',
    '管理员',
    'admin',
    'active'
);
