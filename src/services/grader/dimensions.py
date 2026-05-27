import re


def calculate_word_count_score(answer: str, word_limit: str) -> tuple:
    """计算字数得分"""
    if not word_limit:
        return 10, "字数未指定"

    # Parse word limit (e.g., "150-200字")
    match = re.search(r'(\d+)-(\d+)', word_limit)
    if not match:
        return 10, "字数要求不明确"

    min_words, max_words = int(match.group(1)), int(match.group(2))
    answer_len = len(answer)

    if min_words <= answer_len <= max_words:
        return 10, f"字数符合要求（{answer_len}字）"
    elif answer_len < min_words:
        ratio = answer_len / min_words
        score = max(0, int(10 * ratio))
        return score, f"字数不足（{answer_len}字），要求至少{min_words}字"
    else:
        over_ratio = (answer_len - max_words) / max_words
        score = max(0, int(10 * (1 - over_ratio * 0.5)))
        return score, f"字数超出（{answer_len}字），要求不超过{max_words}字"


def calculate_format_score(answer: str) -> tuple:
    """计算卷面整洁得分"""
    score = 5

    # Check for excessive punctuation
    punct_count = len(re.findall(r'[，。；、：""''（）]', answer))
    if punct_count > len(answer) * 0.3:
        score -= 1

    # Check for line breaks (if present, might be formatted)
    lines = answer.split('\n')
    if len(lines) > 1 and len(lines) < 10:
        score += 0  # Well formatted

    # Check for obvious errors
    if '...' in answer or '～' in answer:
        score -= 1

    return max(0, score), "卷面基本整洁"


def calculate_structure_score(answer: str) -> int:
    """计算逻辑结构得分"""
    score = 0

    # Has clear structure indicators
    structure_markers = ['第一', '第二', '第三', '首先', '其次', '最后', '一是', '二是', '三是']
    for marker in structure_markers:
        if marker in answer:
            score += 5
            break

    # Paragraph count
    paras = [p for p in answer.split('\n') if p.strip()]
    if 2 <= len(paras) <= 5:
        score += 10
    elif len(paras) > 5:
        score += 5

    # Transition words
    transition_words = ['因此', '但是', '然而', '总之', '综上所述']
    for tw in transition_words:
        if tw in answer:
            score += 5
            break

    return min(25, score)


def calculate_dimensions(question: dict, user_answer: str, hit_points: list, missing_points: list) -> dict:
    """计算各维度得分"""
    word_limit = question.get('word_limit', '')

    word_score, word_comment = calculate_word_count_score(user_answer, word_limit)
    format_score, format_comment = calculate_format_score(user_answer)
    structure_score = calculate_structure_score(user_answer)

    # 踩点命中由主评分函数计算
    key_points = question.get('key_points', [])
    hit_rate = len(hit_points) / max(len(key_points), 1)
    hit_score = int(40 * hit_rate)

    # 语言规范（简化计算）
    language_score = 14  # 默认分

    return {
        "踩点命中": hit_score,
        "逻辑结构": structure_score,
        "语言规范": language_score,
        "字数控制": word_score,
        "卷面整洁": format_score
    }
