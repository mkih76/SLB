# AI Grading Prompts

GRADING_SYSTEM_PROMPT = """你是一位资深的申论阅卷老师，具有多年公务员申论阅卷经验。你的任务是严格按照评分标准对学生答案进行批改。

评分维度及权重：
1. 踩点命中（40%）：是否命中标准答案中的采分点
2. 逻辑结构（25%）：答案是否有清晰的层次和逻辑
3. 语言规范（20%）：是否使用规范的政务用语
4. 字数控制（10%）：是否符合字数要求
5. 卷面整洁（5%）：标点、格式是否规范

请严格按照JSON格式输出评分结果，不要添加任何解释。"""


def build_grading_prompt(question: dict, user_answer: str, material: list = None) -> list:
    """构建批改prompt"""
    prompt = f"""题目类型：{question.get('type', '未知')}
题目：{question.get('stem', '')}

字数要求：{question.get('word_limit', '未指定')}

标准答案采分点："""

    key_points = question.get('key_points', [])
    for i, point in enumerate(key_points, 1):
        alias_text = ', '.join(point.get('alias', []))
        prompt += f"\n{i}. {point['point']}（{point['score']}分）"
        if alias_text:
            prompt += f" - 同义表达：{alias_text}"

    if material:
        prompt += "\n\n给定材料：\n"
        for i, seg in enumerate(material, 1):
            prompt += f"\n[材料{i}] {seg}"

    prompt += f"\n\n考生答案：\n{user_answer}"

    prompt += """

请对考生答案进行批改，并严格按以下JSON格式输出（只输出JSON，不要其他内容）：
{
    "score": 总分（0-100）,
    "dimension_scores": {
        "踩点命中": 得分（0-40）,
        "逻辑结构": 得分（0-25）,
        "语言规范": 得分（0-20）,
        "字数控制": 得分（0-10）,
        "卷面整洁": 得分（0-5）
    },
    "hit_points": ["命中的采分点列表"],
    "missing_points": ["遗漏的采分点列表"],
    "ai_feedback": "详细批改意见（指出优点和不足）",
    "improving_suggestions": "改进建议"
}"""

    return [
        {"role": "system", "content": GRADING_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]


def build_simple_feedback_prompt(question: dict, user_answer: str) -> str:
    """构建简化反馈prompt（免费用户）"""
    return f"""题目：{question.get('stem', '')}
考生答案：{user_answer}

请给出简要评价（100字以内），指出主要问题。
格式：得分：XX分\n简要评价：..."""
