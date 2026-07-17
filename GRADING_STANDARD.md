# SLB AI 批改标准体系设计

**版本：** v1.0
**日期：** 2026-05-27

---

## 一、现有批改系统分析

### 1.1 当前架构

双轨制批改路径：

| 路径 | 适用用户 | 实现方式 |
|------|----------|----------|
| 完整批改 | 付费/VIP 用户 | LLM 返回结构化 JSON，五维度打分 |
| 简易反馈 | 免费用户 | LLM 返回 100 字以内的简评 + 一个总分 |

两条路径都依赖 LLM（GPT-4o-mini 或 DeepSeek），核心逻辑写在 Prompt 里。

### 1.2 当前五维度评分标准

| 维度 | 权重 | 满分 | 计算方式 | 问题 |
|------|------|------|----------|------|
| 踩点命中 | 40% | 40 | `hit_rate × 40`，关键词 + alias 匹配 | 仅精确匹配，缺语义理解 |
| 逻辑结构 | 25% | 25 | 序数词(+5)、段落数(+10)、过渡词(+5) | 仅检测形式标记 |
| 语言规范 | 20% | 14 | **硬编码返回 14 分** | 完全是摆设 |
| 字数控制 | 10% | 10 | 正常满分，超/少按比例扣 | 逻辑合理 |
| 卷面整洁 | 5% | 5 | 标点密度>30% 扣1，出现 `...` 扣1 | 过于简单 |

**总分上限是 94 分而非 100 分** —— 语言规范满分只有 14，这是 bug。

### 1.3 三大核心缺陷

**缺陷一：不区分题型**
所有题型用同一套权重，但真实阅卷中五种题型评分逻辑完全不同。

**缺陷二：语言规范是假的**
`dimensions.py` 里语言规范硬编码返回 14 分，无任何实际检测。

**缺陷三：踩点匹配太粗**
关键词 + alias 精确匹配，无法识别语义等价表述。

---

## 二、真实阅卷标准

### 2.1 阅卷机制

申论阅卷采用**双评制**：每份试卷由两位阅卷老师独立打分，分差在阈值内取平均值，超过阈值则三评。阅卷老师有严格的评分细则（细化到每个采分点的分值分配）。

**核心原则：按点给分，采意不采点。**

不要求考生用原话，只要意思对了就给分。

### 2.2 归纳概括题（通常 15-20 分）

```
评分逻辑：按点赋分

每个要点 2-3 分：
  - 满分要点：意思完整、表述准确 → 满分
  - 半分要点：提到但不完整 → 一半分
  - 不给分：完全没提到或理解错误 → 0分

扣分项：
  - 照抄材料原文超过 50% → 该要点最高得一半分
  - 出现与材料无关的主观臆断 → 扣 1-2 分
  - 条理不清、没有分条作答 → 扣 1-2 分
```

### 2.3 综合分析题（通常 15-20 分）

```
评分逻辑：结构分 + 要点分

结构分（3-5 分）：
  - 有总论点句 → +1
  - 有分析层次（是什么/为什么/怎么办）→ +2
  - 有总结/升华 → +1

要点分（10-15 分）：
  - 每个分析要点 2-3 分
  - 要求有材料支撑，不能空谈

扣分项：
  - 只有观点没有分析 → 扣一半分
  - 逻辑链断裂 → 扣 2-3 分
  - 观点与材料矛盾 → 该要点 0 分
```

### 2.4 提出对策题（通常 20-25 分）

```
评分逻辑：问题定位分 + 对策分

问题定位（5 分）：
  - 准确概括出需要解决的问题 → 满分
  - 问题概括不准确 → 扣 2-3 分

对策分（15-20 分）：
  每条对策需满足：
  - 针对性：必须针对具体问题（不是万能对策）
  - 可操作性：有明确的"谁来做 + 做什么 + 怎么做"
  - 合理性：在现实条件下可行

  满足全部 → 满分
  缺少"谁来做" → 扣 1 分
  是万能对策 → 该条最多得 1 分

扣分项：
  - 对策全部是万能对策 → 最高 10 分
  - 对策与问题不对应 → 该条 0 分
```

### 2.5 贯彻执行题（通常 20-25 分）

```
评分逻辑：格式分 + 内容分 + 语言分

格式分（5-8 分）：
  不同文种有不同格式要求：
  - 讲话稿：称谓 + 开场白 + 结束语
  - 倡议书：标题 + 称谓 + 正文 + 落款
  - 调研报告：标题 + 正文（背景+分析+建议）
  - 工作方案：标题 + 正文（目标+措施+保障）
  - 短评：标题 + 正文（观点+论证+结论）
  - 编者按：无标题，直接正文

  格式完整 → 满分
  缺少标题 → 扣 2 分
  缺少称谓/落款 → 扣 1-2 分

内容分（12-15 分）：
  - 是否完成写作目的
  - 内容要点是否齐全

语言分（3-5 分）：
  - 语气是否符合文种
  - 对象是否准确
```

### 2.6 大作文（通常 35-40 分）

```
评分逻辑：分档赋分

一档（32-40分）：
  - 立意准确，紧扣题意
  - 论证充实，有理有据
  - 结构完整，逻辑清晰
  - 语言流畅，有申论语感

二档（24-31分）：
  - 立意基本准确
  - 论证基本充实
  - 结构基本完整
  - 语言基本通顺

三档（16-23分）：
  - 立意有偏差
  - 论证单薄
  - 结构不完整
  - 语言有语病

四档（0-15分）：
  - 立意严重偏离
  - 未完成写作
  - 抄袭材料为主
  - 字数严重不足

加分项：
  - 标题新颖、有文采 → +1-2
  - 结尾有升华 → +1-2
  - 使用时政热词 → +1

扣分项：
  - 没有标题 → 扣 2 分
  - 字数不足 800 字 → 降一档
  - 大段照抄材料 → 视为抄袭，最高三档
```

---

## 三、改进方案：分题型批改标准

### 3.1 架构升级

```
用户提交答案
    ↓
判断题型（guina/zonghe/duice/zhixing/zuowen）
    ↓
选择对应题型的 Prompt 模板
    ↓
本地规则预处理（字数、格式、关键词匹配）
    ↓
调用 LLM（结构化 JSON 输出）
    ↓
本地规则校验 + LLM 分数融合
    ↓
生成批改结果
```

### 3.2 分题型维度权重

```python
QUESTION_TYPE_DIMENSIONS = {
    "guina": {  # 归纳概括
        "point_coverage": 0.70,    # 踩点命中
        "conciseness": 0.15,       # 语言简洁
        "accuracy": 0.10,          # 归纳准确
        "format": 0.05             # 条理清晰
    },
    "zonghe": {  # 综合分析
        "logic_chain": 0.30,       # 逻辑链完整性
        "point_coverage": 0.30,    # 要点覆盖
        "depth": 0.20,             # 分析深度
        "language": 0.10,          # 语言规范
        "format": 0.10             # 格式规范
    },
    "duice": {  # 提出对策
        "problem_identification": 0.20,  # 问题定位
        "targeting": 0.25,               # 针对性
        "feasibility": 0.25,             # 可行性
        "specificity": 0.20,             # 具体性
        "format": 0.10                   # 格式规范
    },
    "zhixing": {  # 贯彻执行
        "format_correctness": 0.20,      # 格式正确性
        "purpose_achievement": 0.25,     # 目的达成度
        "content_completeness": 0.30,    # 内容完整性
        "language_appropriateness": 0.15,# 语言得体性
        "word_count": 0.10               # 字数控制
    },
    "zuowen": {  # 大作文
        "thesis_accuracy": 0.25,    # 立意准确度
        "argument_richness": 0.25,  # 论证充实度
        "structure": 0.20,          # 结构完整性
        "language": 0.20,           # 语言表达
        "innovation": 0.10          # 创新亮点
    }
}
```

### 3.3 分题型 Prompt 模板

#### 归纳概括题 Prompt

```python
GUINA_SYSTEM_PROMPT = """你是申论阅卷专家，专门负责归纳概括题的评分。

评分原则：
1. 按点给分，采意不采点（意思对即可，不要求原话）
2. 照抄材料原文超过50%的要点，最高得一半分
3. 出现主观臆断的扣1-2分
4. 条理不清的扣1-2分

评分维度及权重：
- 踩点命中（70%）：逐条对照参考要点，标注命中/遗漏/多余
- 语言简洁（15%）：是否废话过多、是否照抄原文
- 归纳准确（10%）：概括是否准确反映材料原意
- 条理清晰（5%）：是否分条作答、逻辑是否清楚"""

GUINA_USER_PROMPT = """请对以下归纳概括题进行评分。

【题目】{question_text}
【字数要求】{word_limit}
【参考要点及分值】
{scoring_rubric}

【考生答案】
{user_answer}

请严格按照以下 JSON 格式输出：
{{
    "score": 0-100的总分,
    "dimension_scores": {{
        "point_coverage": 0-70,
        "conciseness": 0-15,
        "accuracy": 0-10,
        "format": 0-5
    }},
    "hit_points": [
        {{"point": "命中的要点", "score": 得分, "max_score": 满分}}
    ],
    "missing_points": [
        {{"point": "遗漏的要点", "max_score": 满分}}
    ],
    "extra_points": [
        {{"point": "多余的表述（主观臆断）", "penalty": 扣分}}
    ],
    "ai_feedback": "详细的逐条分析",
    "improving_suggestions": ["建议1", "建议2"]
}}"""
```

#### 综合分析题 Prompt

```python
ZONGHE_SYSTEM_PROMPT = """你是申论阅卷专家，专门负责综合分析题的评分。

评分原则：
1. 结构分 + 要点分分开评判
2. 必须有完整的逻辑链：是什么→为什么→怎么办
3. 每个层次必须有材料支撑，不能空谈
4. 只有观点没有分析的，扣一半分

评分维度及权重：
- 逻辑链完整性（30%）：是否有"表现→原因→影响→对策"的完整链条
- 要点覆盖（30%）：分析要点是否齐全
- 分析深度（20%）：是否理解材料本质含义
- 语言规范（10%）：是否有申论语感
- 格式规范（10%）：是否有总论点句、总结句"""

ZONGHE_USER_PROMPT = """请对以下综合分析题进行评分。

【题目】{question_text}
【字数要求】{word_limit}
【材料】
{material}

【参考要点及分值】
{scoring_rubric}

【考生答案】
{user_answer}

请重点检查：
1. 是否有总论点句
2. 逻辑链是否完整（是否有断裂、跳跃）
3. 每个分析层次是否有材料支撑
4. 是否有总结/升华

请严格按照以下 JSON 格式输出：
{{
    "score": 0-100,
    "dimension_scores": {{
        "logic_chain": 0-30,
        "point_coverage": 0-30,
        "depth": 0-20,
        "language": 0-10,
        "format": 0-10
    }},
    "logic_chain_analysis": {{
        "has_thesis": true/false,
        "has_what": true/false,      # 是什么
        "has_why": true/false,       # 为什么
        "has_how": true/false,       # 怎么办
        "has_conclusion": true/false,
        "chain_breaks": ["断裂处描述"]
    }},
    "hit_points": [...],
    "missing_points": [...],
    "ai_feedback": "详细分析",
    "improving_suggestions": [...]
}}"""
```

#### 提出对策题 Prompt

```python
DUICE_SYSTEM_PROMPT = """你是申论阅卷专家，专门负责提出对策题的评分。

评分原则：
1. 每条对策必须满足三个条件：针对性、可操作性、合理性
2. 万能对策（如"加强宣传教育"、"完善法律法规"）最多得1分
3. 对策必须与问题对应，不对应该条0分
4. 对策要有明确的"主体+手段+内容"

评分维度及权重：
- 问题定位（20%）：是否准确概括了需要解决的问题
- 针对性（25%）：对策是否针对具体问题
- 可行性（25%）：是否在现实条件下可执行
- 具体性（20%）：是否有"谁来做+做什么+怎么做"
- 格式规范（10%）：条理是否清晰"""

DUICE_USER_PROMPT = """请对以下提出对策题进行评分。

【题目】{question_text}
【字数要求】{word_limit}
【材料】
{material}

【需要解决的问题】
{problem_description}

【考生答案】
{user_answer}

请重点检查每条对策：
1. 是否针对具体问题（而非万能对策）
2. 是否有明确的执行主体
3. 是否有具体的操作步骤
4. 是否在现实中可行

万能对策识别标准：缺少具体执行主体、缺少具体操作内容、适用于任何问题的对策。

请严格按照以下 JSON 格式输出：
{{
    "score": 0-100,
    "dimension_scores": {{
        "problem_identification": 0-20,
        "targeting": 0-25,
        "feasibility": 0-25,
        "specificity": 0-20,
        "format": 0-10
    }},
    "problem_accuracy": "问题定位是否准确的分析",
    "countermeasures": [
        {{
            "content": "对策原文",
            "targeting_score": 0-25,
            "feasibility_score": 0-25,
            "specificity_score": 0-20,
            "is_generic": true/false,
            "feedback": "该条对策的评价"
        }}
    ],
    "generic_countermeasures": ["识别出的万能对策"],
    "ai_feedback": "详细分析",
    "improving_suggestions": [...]
}}"""
```

#### 贯彻执行题 Prompt

```python
ZHIXING_SYSTEM_PROMPT = """你是申论阅卷专家，专门负责贯彻执行题的评分。

评分原则：
1. 不同文种有不同的格式要求，必须按文种评判
2. 格式分、内容分、语言分分开评判
3. 语气必须符合文种和对象

文种格式要求：
- 讲话稿：称谓（各位领导/同志们）+ 开场白 + 主体 + 结束语
- 倡议书：标题（关于...的倡议书）+ 称谓 + 正文 + 倡议号召 + 落款
- 调研报告：标题 + 正文（背景/现状 + 分析 + 建议）
- 工作方案：标题 + 正文（目标 + 措施 + 保障机制）
- 短评：标题 + 正文（引出观点 + 论证 + 结论）
- 导言：无标题，直接正文（背景 + 内容概述 + 意义）
- 编者按：无标题，无称谓，直接正文
- 公开信：标题 + 称谓 + 正文 + 结束语 + 落款
- 简报：标题 + 正文（情况 + 做法 + 成效）

评分维度及权重：
- 格式正确性（20%）：标题/称谓/落款是否符合文种
- 目的达成度（25%）：是否完成写作目的
- 内容完整性（30%）：背景/主体/结尾是否齐全
- 语言得体性（15%）：语气是否符合文种和对象
- 字数控制（10%）：是否在字数范围内"""

ZHIXING_USER_PROMPT = """请对以下贯彻执行题进行评分。

【题目】{question_text}
【文种】{document_type}
【字数要求】{word_limit}
【写作目的】{writing_purpose}
【材料】
{material}

【考生答案】
{user_answer}

请严格按照{document_type}的格式要求评判。

请严格按照以下 JSON 格式输出：
{{
    "score": 0-100,
    "dimension_scores": {{
        "format_correctness": 0-20,
        "purpose_achievement": 0-25,
        "content_completeness": 0-30,
        "language_appropriateness": 0-15,
        "word_count": 0-10
    }},
    "format_check": {{
        "has_title": true/false,
        "title_correct": true/false,
        "has_salutation": true/false,
        "salutation_correct": true/false,
        "has_closing": true/false,
        "has_signature": true/false,
        "format_issues": ["格式问题描述"]
    }},
    "content_check": {{
        "has_background": true/false,
        "has_main_body": true/false,
        "has_conclusion": true/false,
        "purpose_achieved": true/false,
        "missing_elements": ["缺失要素"]
    }},
    "hit_points": [...],
    "missing_points": [...],
    "ai_feedback": "详细分析",
    "improving_suggestions": [...]
}}"""
```

#### 大作文 Prompt

```python
ZUOWEN_SYSTEM_PROMPT = """你是申论阅卷专家，专门负责大作文的评分。

评分原则：
1. 采用分档赋分制，先定档再给分
2. 立意准确是第一标准，立意偏差直接降档
3. 论证必须有材料或时政支撑，不能空谈
4. 大段照抄材料视为抄袭，最高三档

分档标准：
一档（32-40分）：立意准确、论证充实、结构完整、语言流畅
二档（24-31分）：立意基本准确、论证基本充实、结构基本完整
三档（16-23分）：立意有偏差、论证单薄、结构不完整
四档（0-15分）：立意严重偏离、未完成、抄袭为主

评分维度及权重：
- 立意准确度（25%）：中心论点是否切合题意和材料
- 论证充实度（25%）：论据是否充分、论证方法是否多样
- 结构完整性（20%）：标题/开头/分论点/结尾是否完整
- 语言表达（20%）：是否有申论语感、是否口语化
- 创新亮点（10%）：标题新颖、结尾升华、时政热词"""

ZUOWEN_USER_PROMPT = """请对以下大作文进行评分。

【题目】{question_text}
【字数要求】{word_limit}
【材料主旨】{material_theme}

【考生答案】
{user_answer}

请按照以下步骤评分：
1. 先判断立意是否准确（是否切合题意和材料主旨）
2. 根据立意确定所属档次
3. 在档次内根据各维度表现给出具体分数
4. 检查是否有加分项（标题新颖、结尾升华、时政热词）
5. 检查是否有扣分项（无标题、字数不足、抄袭材料）

请严格按照以下 JSON 格式输出：
{{
    "score": 0-40,
    "tier": "一档/二档/三档/四档",
    "tier_reason": "定档理由",
    "dimension_scores": {{
        "thesis_accuracy": 0-25,
        "argument_richness": 0-25,
        "structure": 0-20,
        "language": 0-20,
        "innovation": 0-10
    }},
    "thesis_analysis": {{
        "main_thesis": "考生的中心论点",
        "is_accurate": true/false,
        "deviation_degree": "准确/基本准确/有偏差/严重偏离"
    }},
    "argument_analysis": {{
        "argument_count": 论据数量,
        "has_material_evidence": true/false,
        "has_current_affairs": true/false,
        "argument_methods": ["举例论证", "对比论证", "道理论证"]
    }},
    "structure_analysis": {{
        "has_title": true/false,
        "has_opening": true/false,
        "sub_thesis_count": 分论点数量,
        "has_conclusion": true/false,
        "has_sublimation": true/false
    }},
    "bonus_points": [
        {{"reason": "加分理由", "score": 1-2}}
    ],
    "penalty_points": [
        {{"reason": "扣分理由", "score": -1到-5}}
    ],
    "ai_feedback": "详细分析",
    "improving_suggestions": [...]
}}"""
```

---

## 四、本地规则检测模块

### 4.1 字数检测

```python
import re

def count_chinese_chars(text):
    """统计中文字符数（不含标点）"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))

def check_word_count(text, word_limit_str):
    """
    检查字数是否符合要求
    word_limit_str 格式: "150-200字" 或 "不少于800字" 或 "1000字左右"
    """
    chars = count_chinese_chars(text)

    # 解析字数要求
    range_match = re.search(r'(\d+)-(\d+)字', word_limit_str)
    min_match = re.search(r'不少于(\d+)字', word_limit_str)
    around_match = re.search(r'(\d+)字左右', word_limit_str)

    if range_match:
        min_words = int(range_match.group(1))
        max_words = int(range_match.group(2))
        if min_words <= chars <= max_words:
            return {'status': 'ok', 'score_ratio': 1.0, 'chars': chars}
        elif chars < min_words:
            ratio = chars / min_words
            return {'status': 'under', 'score_ratio': ratio, 'chars': chars}
        else:
            ratio = max_words / chars
            return {'status': 'over', 'score_ratio': ratio, 'chars': chars}

    elif min_match:
        min_words = int(min_match.group(1))
        if chars >= min_words:
            return {'status': 'ok', 'score_ratio': 1.0, 'chars': chars}
        else:
            ratio = chars / min_words
            return {'status': 'under', 'score_ratio': ratio, 'chars': chars}

    elif around_match:
        target = int(around_match.group(1))
        deviation = abs(chars - target) / target
        if deviation <= 0.1:
            return {'status': 'ok', 'score_ratio': 1.0, 'chars': chars}
        else:
            ratio = 1 - deviation
            return {'status': 'deviated', 'score_ratio': max(0.5, ratio), 'chars': chars}

    return {'status': 'unknown', 'score_ratio': 1.0, 'chars': chars}
```

### 4.2 口语化检测

```python
COLLOQUIAL_PATTERNS = [
    # 第一人称口语
    r'我觉得', r'我认为', r'我想', r'在我看来',
    # 口语连接词
    r'然后呢', r'所以说', r'其实吧', r'怎么说呢',
    # 口语程度副词
    r'特别特别', r'非常非常', r'超级',
    # 网络用语
    r'内卷', r'躺平', r'摆烂', r'绝绝子', r'yyds',
    # 不规范省略
    r'etc\.', r'等等等',
    # 感叹号过多
    r'！{3,}',
    r'!{3,}',
]

FORMAL_PHRASES = [
    # 标准申论用语
    '统筹推进', '着力构建', '深入推进', '全面加强',
    '坚持问题导向', '坚持系统观念', '坚持底线思维',
    '以人民为中心', '新发展理念', '高质量发展',
    '治理体系和治理能力现代化', '共建共治共享',
    '放管服改革', '供给侧结构性改革',
    '绿水青山就是金山银山',
    '乡村振兴战略', '新型城镇化',
    '基层社会治理', '网格化管理',
    '数字政府', '智慧城市',
]

def detect_colloquial(text):
    """检测口语化表达"""
    issues = []
    for pattern in COLLOQUIAL_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            issues.append({
                'type': 'colloquial',
                'pattern': pattern,
                'count': len(matches),
                'examples': matches[:3]
            })
    return issues

def detect_formal_language(text):
    """检测是否使用了申论规范用语"""
    found = []
    for phrase in FORMAL_PHRASES:
        if phrase in text:
            found.append(phrase)
    return found

def calculate_language_score(text):
    """计算语言规范得分（0-20分）"""
    score = 20  # 满分起步

    # 口语化扣分
    colloquial = detect_colloquial(text)
    for issue in colloquial:
        score -= issue['count'] * 2
        if score < 0:
            score = 0

    # 规范用语加分（但不超过20）
    formal = detect_formal_language(text)
    score = min(20, score + len(formal) * 1)

    return max(0, min(20, score))
```

### 4.3 格式检测

```python
DOCUMENT_FORMAT_RULES = {
    "讲话稿": {
        "required": ["salutation", "opening", "main_body", "closing"],
        "optional": ["title"],
        "salutation_patterns": [r'各位领导', r'同志们', r'各位来宾', r'朋友们'],
        "closing_patterns": [r'谢谢大家', r'谢谢', r'我的发言完毕']
    },
    "倡议书": {
        "required": ["title", "salutation", "main_body", "call_to_action", "signature"],
        "optional": [],
        "title_patterns": [r'关于.*的倡议书', r'倡议书'],
        "salutation_patterns": [r'各位', r'广大.*朋友们', r'亲爱的'],
        "signature_patterns": [r'倡议人', r'发起人', r'\d{4}年\d{1,2}月']
    },
    "调研报告": {
        "required": ["title", "main_body"],
        "optional": ["subtitle"],
        "title_patterns": [r'关于.*的调研报告', r'关于.*的调查报告', r'调研报告'],
        "structure": ["background", "analysis", "suggestion"]
    },
    "工作方案": {
        "required": ["title", "main_body"],
        "optional": [],
        "title_patterns": [r'关于.*的工作方案', r'关于.*的实施方案', r'工作方案'],
        "structure": ["objective", "measures", "guarantee"]
    },
    "短评": {
        "required": ["title", "main_body"],
        "optional": [],
        "title_patterns": [r'.*'],  # 标题形式灵活
        "structure": ["viewpoint", "argument", "conclusion"]
    },
    "编者按": {
        "required": ["main_body"],
        "optional": [],
        "no_title": True,
        "no_salutation": True
    },
    "公开信": {
        "required": ["title", "salutation", "main_body", "closing", "signature"],
        "optional": [],
        "title_patterns": [r'致.*的公开信', r'公开信'],
        "salutation_patterns": [r'亲爱的', r'尊敬的']
    }
}

def check_document_format(text, doc_type):
    """检查文档格式是否符合文种要求"""
    rules = DOCUMENT_FORMAT_RULES.get(doc_type, {})
    if not rules:
        return {'status': 'unknown', 'issues': ['未知文种']}

    issues = []
    checks = {}

    # 检查标题
    lines = text.strip().split('\n')
    first_line = lines[0].strip() if lines else ''

    if rules.get('no_title'):
        checks['has_title'] = False  # 不应有标题
    elif 'title' in rules.get('required', []):
        has_title = False
        for pattern in rules.get('title_patterns', []):
            if re.search(pattern, first_line):
                has_title = True
                break
        checks['has_title'] = has_title
        if not has_title:
            issues.append('缺少标题或标题格式不正确')

    # 检查称谓
    if rules.get('no_salutation'):
        checks['has_salutation'] = False
    elif 'salutation' in rules.get('required', []):
        has_salutation = False
        for pattern in rules.get('salutation_patterns', []):
            if re.search(pattern, text[:200]):  # 称谓通常在前200字
                has_salutation = True
                break
        checks['has_salutation'] = has_salutation
        if not has_salutation:
            issues.append('缺少称谓')

    # 检查落款
    if 'signature' in rules.get('required', []):
        has_signature = False
        for pattern in rules.get('signature_patterns', []):
            if re.search(pattern, text[-200:]):  # 落款通常在最后200字
                has_signature = True
                break
        checks['has_signature'] = has_signature
        if not has_signature:
            issues.append('缺少落款')

    return {'checks': checks, 'issues': issues}
```

### 4.4 万能对策检测

```python
GENERIC_COUNTERMEASURES = [
    '加强宣传教育',
    '加大宣传力度',
    '完善法律法规',
    '加强制度建设',
    '健全体制机制',
    '加强组织领导',
    '加大资金投入',
    '加强监督考核',
    '建立长效机制',
    '提高思想认识',
    '强化责任落实',
    '营造良好氛围',
    '加强协调配合',
    '加大处罚力度',
    '严格执法',
]

GENERIC_PATTERNS = [
    r'加强.*教育',
    r'加大.*力度',
    r'完善.*制度',
    r'健全.*机制',
    r'提高.*认识',
    r'强化.*落实',
    r'营造.*氛围',
]

def detect_generic_countermeasures(text):
    """检测万能对策"""
    found = []

    # 精确匹配
    for gc in GENERIC_COUNTERMEASURES:
        if gc in text:
            found.append({
                'content': gc,
                'type': 'exact_match'
            })

    # 模式匹配
    for pattern in GENERIC_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in [f['content'] for f in found]:
                found.append({
                    'content': match,
                    'type': 'pattern_match'
                })

    return found

def check_countermeasure_quality(countermeasure_text):
    """检查单条对策的质量"""
    score = 100
    feedback = []

    # 检查是否万能对策
    generic = detect_generic_countermeasures(countermeasure_text)
    if generic:
        score -= 40
        feedback.append('包含万能对策表述，缺少具体性')

    # 检查是否有执行主体
    subject_patterns = [r'政府', r'企业', r'社区', r'学校', r'医院', r'部门', r'机构']
    has_subject = any(re.search(p, countermeasure_text) for p in subject_patterns)
    if not has_subject:
        score -= 20
        feedback.append('缺少明确的执行主体')

    # 检查是否有具体操作
    action_patterns = [r'通过', r'采取', r'实施', r'推行', r'建立', r'设立', r'开展']
    has_action = any(re.search(p, countermeasure_text) for p in action_patterns)
    if not has_action:
        score -= 20
        feedback.append('缺少具体的操作手段')

    # 检查是否有预期效果
    effect_patterns = [r'从而', r'进而', r'以此', r'以便', r'促进', r'推动', r'实现']
    has_effect = any(re.search(p, countermeasure_text) for p in effect_patterns)
    if not has_effect:
        score -= 10
        feedback.append('缺少预期效果描述')

    return {
        'score': max(0, score),
        'feedback': feedback,
        'has_subject': has_subject,
        'has_action': has_action,
        'has_effect': has_effect,
        'is_generic': len(generic) > 0
    }
```

### 4.5 逻辑链检测

```python
def detect_logic_chain(text):
    """检测综合分析题的逻辑链"""
    result = {
        'has_thesis': False,
        'has_what': False,
        'has_why': False,
        'has_how': False,
        'has_conclusion': False,
        'chain_breaks': []
    }

    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    # 检测总论点句（通常在第一段）
    thesis_patterns = [r'这表明', r'这说明', r'由此可见', r'因此', r'总之']
    first_para = paragraphs[0] if paragraphs else ''
    result['has_thesis'] = any(re.search(p, first_para) for p in thesis_patterns)

    # 检测"是什么"层次
    what_patterns = [r'是指', r'即', r'所谓', r'本质上', r'具体来说']
    result['has_what'] = any(
        any(re.search(p, para) for p in what_patterns)
        for para in paragraphs
    )

    # 检测"为什么"层次
    why_patterns = [r'原因', r'因为', r'由于', r'根源', r'导致', r'之所以']
    result['has_why'] = any(
        any(re.search(p, para) for p in why_patterns)
        for para in paragraphs
    )

    # 检测"怎么办"层次
    how_patterns = [r'应该', r'需要', r'必须', r'建议', r'对策', r'措施']
    result['has_how'] = any(
        any(re.search(p, para) for p in how_patterns)
        for para in paragraphs
    )

    # 检测总结句（通常在最后一段）
    last_para = paragraphs[-1] if paragraphs else ''
    conclusion_patterns = [r'总之', r'综上', r'因此', r'只有.*才能', r'唯有']
    result['has_conclusion'] = any(re.search(p, last_para) for p in conclusion_patterns)

    # 检测逻辑链断裂
    if result['has_what'] and not result['has_why']:
        result['chain_breaks'].append('有"是什么"但缺少"为什么"分析')
    if result['has_why'] and not result['has_how']:
        result['chain_breaks'].append('有"为什么"但缺少"怎么办"对策')
    if not result['has_thesis'] and not result['has_conclusion']:
        result['chain_breaks'].append('缺少总论点句和总结句')

    return result
```

---

## 五、LLM 与本地规则融合策略

### 5.1 融合原则

```
本地规则优先用于：
  - 字数检测（精确）
  - 格式检测（精确）
  - 口语化检测（精确）
  - 万能对策检测（精确）
  - 关键词匹配（基础）

LLM 优先用于：
  - 语义理解（采意不采点）
  - 逻辑链分析（深层理解）
  - 论证质量评判（主观判断）
  - 语言风格评估（语感判断）
  - 整体立意判断（大作文）
```

### 5.2 分数融合算法

```python
def merge_scores(local_scores, llm_scores, question_type):
    """
    融合本地规则分数和 LLM 分数

    策略：
    - 字数和格式：以本地规则为准
    - 踩点命中：本地规则做下限，LLM 做上限
    - 逻辑结构：以 LLM 为主，本地规则做校验
    - 语言规范：本地规则检测口语化，LLM 评估语感
    - 整体立意：以 LLM 为准
    """
    dimensions = QUESTION_TYPE_DIMENSIONS[question_type]
    merged = {}

    for dim, weight in dimensions.items():
        local = local_scores.get(dim)
        llm = llm_scores.get(dim)

        if dim in ['word_count', 'format']:
            # 字数和格式以本地为准
            merged[dim] = local if local is not None else llm

        elif dim == 'point_coverage':
            # 踩点：取本地和LLM的较高值（本地可能漏判语义等价）
            if local is not None and llm is not None:
                merged[dim] = max(local, llm)
            else:
                merged[dim] = llm if llm is not None else local

        elif dim == 'language':
            # 语言：本地检测口语化扣分 + LLM评估语感
            local_penalty = local_scores.get('colloquial_penalty', 0)
            if llm is not None:
                merged[dim] = max(0, llm - local_penalty)
            else:
                merged[dim] = local

        else:
            # 其他维度以LLM为主
            merged[dim] = llm if llm is not None else local

    return merged
```

### 5.3 批改流程

```python
def grade_answer(pid, qid, user_answer, question, material=None):
    """完整的批改流程"""

    # 1. 获取题型
    question_type = question.get('type', 'guina')

    # 2. 本地规则预处理
    local_results = {}

    # 字数检测
    word_limit = question.get('word_limit', '')
    local_results['word_count'] = check_word_count(user_answer, word_limit)

    # 语言检测
    local_results['colloquial'] = detect_colloquial(user_answer)
    local_results['formal'] = detect_formal_language(user_answer)
    local_results['language_score'] = calculate_language_score(user_answer)

    # 题型特定检测
    if question_type == 'zhixing':
        doc_type = question.get('document_type', '讲话稿')
        local_results['format'] = check_document_format(user_answer, doc_type)

    if question_type == 'duice':
        local_results['generic'] = detect_generic_countermeasures(user_answer)

    if question_type == 'zonghe':
        local_results['logic_chain'] = detect_logic_chain(user_answer)

    # 3. 构建 Prompt 并调用 LLM
    prompt_messages = build_grading_prompt(question, user_answer, material)
    llm_result = call_llm(prompt_messages)

    # 4. 融合分数
    local_scores = extract_local_scores(local_results, question_type)
    llm_scores = llm_result.get('dimension_scores', {})
    merged_scores = merge_scores(local_scores, llm_scores, question_type)

    # 5. 计算总分
    total_score = sum(
        merged_scores.get(dim, 0) * weight
        for dim, weight in QUESTION_TYPE_DIMENSIONS[question_type].items()
    )

    # 6. 生成最终结果
    return {
        'score': round(total_score, 1),
        'dimension_scores': merged_scores,
        'hit_points': llm_result.get('hit_points', []),
        'missing_points': llm_result.get('missing_points', []),
        'ai_feedback': llm_result.get('ai_feedback', ''),
        'improving_suggestions': llm_result.get('improving_suggestions', []),
        'local_checks': local_results,
        'llm_raw': llm_result
    }
```

---

## 六、实施路线

### Phase 1：修复现有 bug（1-2 天）

1. 修复语言规范硬编码 14 分的问题
2. 修复总分上限 94 的问题（改为 100）
3. 统一 LLM 返回分数和本地计算分数的映射

### Phase 2：分题型 Prompt（3-5 天）

1. 实现五套独立的 Prompt 模板
2. 根据 `question.type` 自动选择对应 Prompt
3. 调整 LLM 输出 JSON 格式以适配各题型

### Phase 3：本地规则模块（5-7 天）

1. 实现字数检测模块
2. 实现口语化检测模块
3. 实现格式检测模块（按文种）
4. 实现万能对策检测模块
5. 实现逻辑链检测模块

### Phase 4：分数融合（3-5 天）

1. 实现本地分数和 LLM 分数的融合算法
2. 建立校验机制（本地和 LLM 分差过大时标记）
3. A/B 测试对比融合前后的批改准确率

### Phase 5：持续优化（长期）

1. 收集用户对批改结果的反馈
2. 人工抽查批改准确率
3. 根据反馈迭代 Prompt 和本地规则
4. 建立题型专属的关键词库和同义词库

---

## 七、质量保障

### 7.1 批改一致性

同一份答案多次批改，分数波动应控制在 5 分以内。通过缓存机制和 temperature=0.3 来保证。

### 7.2 批改准确性

人工抽查 100 份批改结果，与真实阅卷老师评分对比：
- 分差在 5 分以内：视为准确
- 准确率目标：≥ 85%

### 7.3 反馈闭环

用户可以对批改结果提出异议，标记"评分偏高"或"评分偏低"。收集反馈用于优化 Prompt。
