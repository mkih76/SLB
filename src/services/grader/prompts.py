# AI Grading Prompts - 分题型 Prompt 模板系统
#
# 五种题型各自独立的 System Prompt 和 User Prompt 构建函数
# 评分标准对标真实申论阅卷规则：按点给分，采意不采点

import json


# ============================================================
# 通用系统角色
# ============================================================

BASE_SYSTEM_ROLE = """你是一位资深的申论阅卷老师，具有多年公务员申论阅卷经验。
核心评分原则：
1. 按点给分，采意不采点（意思对即可，不要求考生用原话）
2. 照抄材料原文超过50%的要点，最高得一半分
3. 出现与材料无关的主观臆断，酌情扣分
4. 条理不清、没有分条作答，酌情扣分

请严格按照JSON格式输出评分结果，不要添加任何解释。"""


# ============================================================
# 题型一：归纳概括
# ============================================================

GUINA_SYSTEM_PROMPT = BASE_SYSTEM_ROLE + """

你正在评阅【归纳概括题】。

评分维度及权重：
1. 踩点命中（70%）：逐条对照参考要点，意思对即可得分
2. 语言简洁（15%）：是否废话过多、是否大段照抄材料原文
3. 归纳准确（10%）：概括是否准确反映材料原意
4. 条理清晰（5%）：是否分条作答、逻辑是否清楚

踩点规则：
- 意思对即可，不要求用原话
- 考生用自己的话概括了要点的核心意思 -> 满分
- 考生提到了但表述不完整 -> 该要点一半分
- 完全没提到 -> 0分
- 照抄材料原文超过50% -> 该要点最高得一半分"""


def build_guina_prompt(question: dict, user_answer: str, material: list = None) -> list:
    """构建归纳概括题的批改 prompt"""
    prompt = f"""题目类型：归纳概括
题目：{question.get('stem', '')}
字数要求：{question.get('word_limit', '未指定')}

参考要点及分值："""

    key_points = question.get('key_points', [])
    for i, point in enumerate(key_points, 1):
        alias_text = ', '.join(point.get('alias', []))
        prompt += f"\n{i}. {point['point']}（{point['score']}分）"
        if alias_text:
            prompt += f" [同义表达：{alias_text}]"

    if material:
        prompt += "\n\n给定材料："
        for i, seg in enumerate(material, 1):
            prompt += f"\n[材料{i}] {seg}"

    prompt += f"""

考生答案：
{user_answer}

请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "score": 总分（0-100）,
    "dimension_scores": {{
        "point_coverage": 踩点命中得分（0-70）,
        "conciseness": 语言简洁得分（0-15）,
        "accuracy": 归纳准确得分（0-10）,
        "format": 条理清晰得分（0-5）
    }},
    "hit_points": [
        {{"point": "命中的要点描述", "score": 得分, "max_score": 该要点满分}}
    ],
    "missing_points": [
        {{"point": "遗漏的要点描述", "max_score": 该要点满分}}
    ],
    "extra_points": [
        {{"point": "多余或主观臆断的表述", "penalty": 扣分}}
    ],
    "ai_feedback": "详细的逐条分析，说明每个要点的命中/遗漏情况",
    "improving_suggestions": ["改进建议1", "改进建议2"]
}}"""

    return [
        {"role": "system", "content": GUINA_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]


# ============================================================
# 题型二：综合分析
# ============================================================

ZONGHE_SYSTEM_PROMPT = BASE_SYSTEM_ROLE + """

你正在评阅【综合分析题】。

评分维度及权重：
1. 逻辑链完整性（30%）：是否有"是什么->为什么->怎么办"的完整链条
2. 要点覆盖（30%）：分析要点是否齐全
3. 分析深度（20%）：是否理解材料本质含义，而非表面罗列
4. 语言规范（10%）：是否有申论语感，是否口语化
5. 格式规范（10%）：是否有总论点句、总结/升华句

逻辑链检测标准：
- 有总论点句（开头点明核心观点）
- 有"是什么"层次（解释概念/现象/表现）
- 有"为什么"层次（分析原因/影响/意义）
- 有"怎么办"层次（提出对策/建议/路径）
- 有总结/升华句（结尾回扣论点）

逻辑链断裂判定：
- 有"是什么"但没有"为什么" -> 断裂
- 有"为什么"但没有"怎么办" -> 断裂
- 跳过中间层次直接给结论 -> 断裂"""


def build_zonghe_prompt(question: dict, user_answer: str, material: list = None) -> list:
    """构建综合分析题的批改 prompt"""
    prompt = f"""题目类型：综合分析
题目：{question.get('stem', '')}
字数要求：{question.get('word_limit', '未指定')}

参考要点及分值："""

    key_points = question.get('key_points', [])
    for i, point in enumerate(key_points, 1):
        alias_text = ', '.join(point.get('alias', []))
        prompt += f"\n{i}. {point['point']}（{point['score']}分）"
        if alias_text:
            prompt += f" [同义表达：{alias_text}]"

    if material:
        prompt += "\n\n给定材料："
        for i, seg in enumerate(material, 1):
            prompt += f"\n[材料{i}] {seg}"

    prompt += f"""

考生答案：
{user_answer}

请重点分析：
1. 是否有总论点句
2. 逻辑链是否完整（是什么->为什么->怎么办），哪里断裂
3. 每个分析层次是否有材料支撑
4. 是否有总结/升华

请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "score": 总分（0-100）,
    "dimension_scores": {{
        "logic_chain": 逻辑链完整性得分（0-30）,
        "point_coverage": 要点覆盖得分（0-30）,
        "depth": 分析深度得分（0-20）,
        "language": 语言规范得分（0-10）,
        "format": 格式规范得分（0-10）
    }},
    "logic_chain_analysis": {{
        "has_thesis": true或false（是否有总论点句）,
        "has_what": true或false（是否有"是什么"层次）,
        "has_why": true或false（是否有"为什么"层次）,
        "has_how": true或false（是否有"怎么办"层次）,
        "has_conclusion": true或false（是否有总结升华）,
        "chain_breaks": ["断裂处描述，如：有'是什么'但缺少'为什么'分析"]
    }},
    "hit_points": [
        {{"point": "命中的要点", "score": 得分, "max_score": 满分}}
    ],
    "missing_points": [
        {{"point": "遗漏的要点", "max_score": 满分}}
    ],
    "ai_feedback": "详细分析，包含逻辑链评价和各层次分析",
    "improving_suggestions": ["改进建议1", "改进建议2"]
}}"""

    return [
        {"role": "system", "content": ZONGHE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]


# ============================================================
# 题型三：提出对策
# ============================================================

DUICE_SYSTEM_PROMPT = BASE_SYSTEM_ROLE + """

你正在评阅【提出对策题】。

评分维度及权重：
1. 问题定位（20%）：是否准确概括了需要解决的问题
2. 针对性（25%）：每条对策是否针对具体问题，而非万能对策
3. 可行性（25%）：对策是否在现实条件下可执行
4. 具体性（20%）：是否有明确的"谁来做+做什么+怎么做"
5. 格式规范（10%）：条理是否清晰

万能对策判定标准（以下类型的对策最多得1分/条）：
- 缺少具体执行主体（如只写"加强宣传教育"而不写谁来宣传、宣传什么）
- 缺少具体操作内容（如只写"完善法律法规"而不写完善哪些、怎么完善）
- 适用于任何问题的泛化对策（换一道题这个对策照样能用）

高质量对策标准：
- 有明确的执行主体（政府部门/企业/社区/社会组织等）
- 有具体的操作手段（通过什么方式、采取什么措施）
- 有预期的效果（从而/进而/以此达到什么目标）
- 针对材料中的具体问题，而非泛泛而谈"""


def build_duice_prompt(question: dict, user_answer: str, material: list = None) -> list:
    """构建提出对策题的批改 prompt"""
    prompt = f"""题目类型：提出对策
题目：{question.get('stem', '')}
字数要求：{question.get('word_limit', '未指定')}

需要解决的问题及分值："""

    key_points = question.get('key_points', [])
    for i, point in enumerate(key_points, 1):
        alias_text = ', '.join(point.get('alias', []))
        prompt += f"\n{i}. {point['point']}（{point['score']}分）"
        if alias_text:
            prompt += f" [同义表达：{alias_text}]"

    if material:
        prompt += "\n\n给定材料："
        for i, seg in enumerate(material, 1):
            prompt += f"\n[材料{i}] {seg}"

    prompt += f"""

考生答案：
{user_answer}

请重点检查每条对策：
1. 是否针对具体问题（还是万能对策）
2. 是否有明确的执行主体
3. 是否有具体的操作步骤
4. 是否在现实中可行

请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "score": 总分（0-100）,
    "dimension_scores": {{
        "problem_identification": 问题定位得分（0-20）,
        "targeting": 针对性得分（0-25）,
        "feasibility": 可行性得分（0-25）,
        "specificity": 具体性得分（0-20）,
        "format": 格式规范得分（0-10）
    }},
    "problem_accuracy": "问题定位是否准确的分析说明",
    "countermeasures": [
        {{
            "content": "考生对策原文",
            "targeting_score": 针对性得分（0-25）,
            "feasibility_score": 可行性得分（0-25）,
            "specificity_score": 具体性得分（0-20）,
            "is_generic": true或false（是否为万能对策）,
            "feedback": "该条对策的评价"
        }}
    ],
    "generic_countermeasures": ["识别出的万能对策原文"],
    "hit_points": [
        {{"point": "对上的问题/对策", "score": 得分, "max_score": 满分}}
    ],
    "missing_points": [
        {{"point": "遗漏的问题/对策", "max_score": 满分}}
    ],
    "ai_feedback": "详细分析，重点评价对策的针对性和可操作性",
    "improving_suggestions": ["改进建议1", "改进建议2"]
}}"""

    return [
        {"role": "system", "content": DUICE_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]


# ============================================================
# 题型四：贯彻执行
# ============================================================

ZHIXING_SYSTEM_PROMPT = BASE_SYSTEM_ROLE + """

你正在评阅【贯彻执行题】。

评分维度及权重：
1. 格式正确性（20%）：标题/称谓/落款是否符合文种要求
2. 目的达成度（25%）：是否完成写作目的（号召/汇报/建议/宣传等）
3. 内容完整性（30%）：背景/主体/结尾是否齐全
4. 语言得体性（15%）：语气是否符合文种和对象
5. 字数控制（10%）：是否在字数范围内

文种格式要求：
- 讲话稿：称谓（各位领导/同志们）+ 开场白 + 主体 + 结束语（谢谢大家）
- 倡议书：标题（关于...的倡议书）+ 称谓 + 正文 + 倡议号召 + 落款
- 调研报告：标题（关于...的调研报告）+ 正文（背景现状 + 分析 + 建议）
- 工作方案：标题（关于...的工作方案/实施方案）+ 正文（目标 + 措施 + 保障）
- 短评：标题 + 正文（引出观点 + 论证 + 结论）
- 导言：无标题，直接正文（背景 + 内容概述 + 意义）
- 编者按：无标题、无称谓，直接正文
- 公开信：标题（致...的公开信）+ 称谓 + 正文 + 结束语 + 落款
- 简报：标题 + 正文（情况 + 做法 + 成效）"""


def build_zhixing_prompt(question: dict, user_answer: str, material: list = None) -> list:
    """构建贯彻执行题的批改 prompt"""
    doc_type = question.get('document_type', '讲话稿')

    prompt = f"""题目类型：贯彻执行
文种：{doc_type}
题目：{question.get('stem', '')}
字数要求：{question.get('word_limit', '未指定')}
写作目的：{question.get('writing_purpose', '未指定')}

参考要点及分值："""

    key_points = question.get('key_points', [])
    for i, point in enumerate(key_points, 1):
        alias_text = ', '.join(point.get('alias', []))
        prompt += f"\n{i}. {point['point']}（{point['score']}分）"
        if alias_text:
            prompt += f" [同义表达：{alias_text}]"

    if material:
        prompt += "\n\n给定材料："
        for i, seg in enumerate(material, 1):
            prompt += f"\n[材料{i}] {seg}"

    prompt += f"""

考生答案：
{user_answer}

请严格按照【{doc_type}】的格式要求评判：
1. 格式是否完整（标题/称谓/落款等）
2. 是否完成写作目的
3. 内容要点是否齐全
4. 语气是否得体

请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "score": 总分（0-100）,
    "dimension_scores": {{
        "format_correctness": 格式正确性得分（0-20）,
        "purpose_achievement": 目的达成度得分（0-25）,
        "content_completeness": 内容完整性得分（0-30）,
        "language_appropriateness": 语言得体性得分（0-15）,
        "word_count": 字数控制得分（0-10）
    }},
    "format_check": {{
        "has_title": true或false,
        "title_correct": true或false,
        "has_salutation": true或false,
        "salutation_correct": true或false,
        "has_closing": true或false,
        "has_signature": true或false,
        "format_issues": ["格式问题描述"]
    }},
    "content_check": {{
        "has_background": true或false,
        "has_main_body": true或false,
        "has_conclusion": true或false,
        "purpose_achieved": true或false,
        "missing_elements": ["缺失的要素"]
    }},
    "hit_points": [
        {{"point": "命中的要点", "score": 得分, "max_score": 满分}}
    ],
    "missing_points": [
        {{"point": "遗漏的要点", "max_score": 满分}}
    ],
    "ai_feedback": "详细分析，包含格式评价、内容完整性评价和语言得体性评价",
    "improving_suggestions": ["改进建议1", "改进建议2"]
}}"""

    return [
        {"role": "system", "content": ZHIXING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]


# ============================================================
# 题型五：大作文
# ============================================================

ZUOWEN_SYSTEM_PROMPT = BASE_SYSTEM_ROLE + """

你正在评阅【大作文】。

大作文采用分档赋分制，先定档再在档内给分：

一档（32-40分）：
  - 立意准确，紧扣题意和材料主旨
  - 论证充实，有理有据（有材料支撑或时政素材）
  - 结构完整，逻辑清晰（标题+开头+分论点段落+结尾）
  - 语言流畅，有申论语感

二档（24-31分）：
  - 立意基本准确，没有明显偏离
  - 论证基本充实，但部分论据单薄
  - 结构基本完整，但段落衔接不够紧密
  - 语言基本通顺，偶有口语化表达

三档（16-23分）：
  - 立意有偏差，未完全切合题意
  - 论证单薄，缺少具体论据
  - 结构不完整，缺少必要组成部分
  - 语言有语病或明显口语化

四档（0-15分）：
  - 立意严重偏离题意
  - 未完成写作（字数严重不足）
  - 大段照抄材料（视为抄袭）
  - 语言混乱，无法理解

加分项（每项+1-2分）：
  - 标题新颖、有文采
  - 结尾有升华（联系时代背景/国家战略）
  - 恰当使用时政热词和规范表述

扣分项：
  - 没有标题 -> 扣2分
  - 字数不足800字 -> 降一档
  - 大段照抄材料 -> 视为抄袭，最高三档

评分维度及权重：
1. 立意准确度（25%）：中心论点是否切合题意和材料主旨
2. 论证充实度（25%）：论据是否充分、论证方法是否多样
3. 结构完整性（20%）：标题/开头/分论点/结尾是否完整
4. 语言表达（20%）：是否有申论语感、是否口语化
5. 创新亮点（10%）：标题新颖、结尾升华、时政热词"""


def build_zuowen_prompt(question: dict, user_answer: str, material: list = None) -> list:
    """构建大作文的批改 prompt"""
    prompt = f"""题目类型：大作文
题目：{question.get('stem', '')}
字数要求：{question.get('word_limit', '不少于1000字')}
材料主旨：{question.get('material_theme', '未指定')}

评分参考："""

    key_points = question.get('key_points', [])
    if key_points:
        for i, point in enumerate(key_points, 1):
            prompt += f"\n{i}. {point['point']}（{point['score']}分）"
    else:
        prompt += "\n（无具体采分点，以立意准确为核心标准）"

    if material:
        prompt += "\n\n给定材料："
        for i, seg in enumerate(material, 1):
            prompt += f"\n[材料{i}] {seg}"

    prompt += f"""

考生答案：
{user_answer}

请按以下步骤评分：
1. 先判断立意是否准确（是否切合题意和材料主旨）
2. 根据立意确定所属档次（一档/二档/三档/四档）
3. 在档次内根据各维度表现给出具体分数
4. 检查是否有加分项（标题新颖、结尾升华、时政热词）
5. 检查是否有扣分项（无标题、字数不足、抄袭材料）

请严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{{
    "score": 总分（0-40）,
    "tier": "一档/二档/三档/四档",
    "tier_reason": "定档理由",
    "dimension_scores": {{
        "thesis_accuracy": 立意准确度得分（0-25）,
        "argument_richness": 论证充实度得分（0-25）,
        "structure": 结构完整性得分（0-20）,
        "language": 语言表达得分（0-20）,
        "innovation": 创新亮点得分（0-10）
    }},
    "thesis_analysis": {{
        "main_thesis": "考生的中心论点（从文章中提炼）",
        "is_accurate": true或false,
        "deviation_degree": "准确/基本准确/有偏差/严重偏离"
    }},
    "argument_analysis": {{
        "argument_count": 论据数量,
        "has_material_evidence": true或false（是否有材料支撑）,
        "has_current_affairs": true或false（是否使用时政素材）,
        "argument_methods": ["使用的论证方法，如举例论证、对比论证、道理论证"]
    }},
    "structure_analysis": {{
        "has_title": true或false,
        "has_opening": true或false,
        "sub_thesis_count": 分论点数量,
        "has_conclusion": true或false,
        "has_sublimation": true或false（结尾是否有升华）
    }},
    "bonus_points": [
        {{"reason": "加分理由", "score": 加分值}}
    ],
    "penalty_points": [
        {{"reason": "扣分理由", "score": 扣分值（负数）}}
    ],
    "hit_points": [
        {{"point": "命中的要点", "score": 得分, "max_score": 满分}}
    ],
    "missing_points": [
        {{"point": "遗漏的要点", "max_score": 满分}}
    ],
    "ai_feedback": "详细分析，包含立意评价、论证评价、结构评价和语言评价",
    "improving_suggestions": ["改进建议1", "改进建议2"]
}}"""

    return [
        {"role": "system", "content": ZUOWEN_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]


# ============================================================
# 题型路由：根据题型选择对应的 Prompt 构建函数
# ============================================================

PROMPT_BUILDERS = {
    'guina': build_guina_prompt,
    'zonghe': build_zonghe_prompt,
    'duice': build_duice_prompt,
    'zhixing': build_zhixing_prompt,
    'zuowen': build_zuowen_prompt,
}


def build_grading_prompt(question: dict, user_answer: str, material: list = None) -> list:
    """根据题型自动选择对应的 Prompt 构建函数

    Args:
        question: 题目信息字典，必须包含 'type' 字段
        user_answer: 考生答案
        material: 给定材料（可选）

    Returns:
        消息列表 [{"role": "system", ...}, {"role": "user", ...}]
    """
    question_type = question.get('type', 'guina')
    builder = PROMPT_BUILDERS.get(question_type, build_guina_prompt)
    return builder(question, user_answer, material)


def build_simple_feedback_prompt(question: dict, user_answer: str) -> str:
    """构建简化反馈 prompt（免费用户）

    返回简要评价，不使用结构化 JSON 输出
    """
    return f"""题目：{question.get('stem', '')}
考生答案：{user_answer}

请给出简要评价（100字以内），指出主要问题和改进方向。
格式：得分：XX分
简要评价：..."""
