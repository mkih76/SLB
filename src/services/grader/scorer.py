# AI 批改核心模块
#
# 负责调用 LLM、融合本地规则、生成最终批改结果
# 支持分题型评分和旧版通用评分两种模式

import json
import logging
from src.services.grader.cache import grader_cache
from src.services.grader.prompts import build_grading_prompt, build_simple_feedback_prompt
from src.services.grader.dimensions import (
    calculate_dimensions,
    calculate_type_dimensions,
    calculate_total_score,
    detect_colloquial,
    detect_formal_language,
    detect_generic_countermeasures,
    detect_logic_chain,
    check_document_format,
    check_countermeasure_quality,
    count_chinese_chars,
)
from src.config import get_llm_config

logger = logging.getLogger(__name__)

# 分题型维度满分映射
TYPE_DIMENSION_MAX = {
    "guina": {
        "point_coverage": 70, "conciseness": 15, "accuracy": 10, "format": 5
    },
    "zonghe": {
        "logic_chain": 30, "point_coverage": 30, "depth": 20, "language": 10, "format": 10
    },
    "duice": {
        "problem_identification": 20, "targeting": 25, "feasibility": 25,
        "specificity": 20, "format": 10
    },
    "zhixing": {
        "format_correctness": 20, "purpose_achievement": 25,
        "content_completeness": 30, "language_appropriateness": 15, "word_count": 10
    },
    "zuowen": {
        "thesis_accuracy": 25, "argument_richness": 25, "structure": 20,
        "language": 20, "innovation": 10
    }
}


def call_llm(messages: list, parse_json: bool = True):
    """调用 LLM API（动态读取配置，支持后台切换模型）

    Args:
        messages: 聊天消息列表
        parse_json: 是否将响应内容解析为 JSON，默认 True

    Returns:
        解析后的 dict 或原始文本
    """
    import requests

    llm = get_llm_config()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm['api_key']}"
    }

    data = {
        "model": llm['model'],
        "messages": messages,
        "temperature": llm['temperature'],
        "max_tokens": llm['max_tokens']
    }

    try:
        response = requests.post(
            f"{llm['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        if parse_json:
            # 处理 LLM 可能在 JSON 前后添加的 markdown 标记
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            return json.loads(content.strip())
        return content
    except json.JSONDecodeError as e:
        logger.error(f"LLM 返回的 JSON 解析失败: {e}, 原始内容: {content[:500]}")
        raise Exception(f"LLM 返回格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        raise Exception(f"LLM调用失败: {str(e)}")


def _clamp(value, min_val, max_val):
    """将值限制在指定范围内"""
    return max(min_val, min(max_val, value))


def _normalize_llm_scores(llm_scores: dict, dimension_max: dict) -> dict:
    """校验并修正 LLM 返回的维度分数，确保不超出满分范围

    Args:
        llm_scores: LLM 返回的原始维度分数
        dimension_max: 各维度满分

    Returns:
        修正后的维度分数
    """
    normalized = {}
    for dim, max_val in dimension_max.items():
        raw = llm_scores.get(dim, 0)
        if isinstance(raw, (int, float)):
            normalized[dim] = _clamp(int(raw), 0, max_val)
        else:
            normalized[dim] = 0
    return normalized


def grade_answer(pid: str, qid: str, question: dict,
                 user_answer: str, material: list = None) -> dict:
    """批改答案（新版分题型评分）

    流程：
    1. 检查缓存
    2. 根据题型选择 Prompt
    3. 调用 LLM 获取评分
    4. 本地规则校验
    5. 融合分数
    6. 缓存并返回结果

    Args:
        pid: 试卷 ID
        qid: 题目 ID
        question: 题目信息字典
        user_answer: 考生答案
        material: 给定材料（可选）

    Returns:
        批改结果字典
    """
    # 1. 检查缓存
    cached = grader_cache.get(pid, qid, user_answer)
    if cached:
        cached['from_cache'] = True
        return cached

    question_type = question.get('type', 'guina')

    # 2. 构建 Prompt 并调用 LLM
    messages = build_grading_prompt(question, user_answer, material)

    try:
        llm_result = call_llm(messages)
    except Exception as e:
        logger.error(f"批改失败 (pid={pid}, qid={qid}): {e}")
        raise Exception(f"批改失败: {str(e)}")

    # 3. 提取 LLM 返回的维度分数
    llm_raw_scores = llm_result.get('dimension_scores', {})
    dimension_max = TYPE_DIMENSION_MAX.get(question_type, TYPE_DIMENSION_MAX['guina'])
    llm_scores = _normalize_llm_scores(llm_raw_scores, dimension_max)

    # 4. 本地规则校验
    local_checks = {}
    local_checks['char_count'] = count_chinese_chars(user_answer)
    local_checks['colloquial'] = detect_colloquial(user_answer)
    local_checks['formal_phrases'] = detect_formal_language(user_answer)

    if question_type == 'zhixing':
        doc_type = question.get('document_type', '讲话稿')
        local_checks['format_check'] = check_document_format(user_answer, doc_type)

    if question_type == 'duice':
        local_checks['generic_countermeasures'] = detect_generic_countermeasures(user_answer)

    if question_type == 'zonghe':
        local_checks['logic_chain'] = detect_logic_chain(user_answer)

    # 5. 融合分数（以 LLM 为主，本地规则做修正）
    merged_scores = dict(llm_scores)

    # 语言维度：扣除本地检测到的口语化扣分
    lang_dim = 'language' if question_type in ('zonghe', 'zuowen') else 'language_appropriateness'
    if lang_dim in merged_scores:
        colloquial_penalty = len(local_checks['colloquial']) * 2
        max_lang = dimension_max.get(lang_dim, 20)
        merged_scores[lang_dim] = _clamp(
            merged_scores[lang_dim] - colloquial_penalty, 0, max_lang
        )

    # 贯彻执行格式：融合本地检测结果
    if question_type == 'zhixing' and 'format_correctness' in merged_scores:
        fmt = local_checks.get('format_check', {})
        local_fmt_ratio = fmt.get('score_ratio', 1.0)
        llm_fmt = merged_scores['format_correctness']
        # 取本地和 LLM 的平均值
        merged_scores['format_correctness'] = int(
            (llm_fmt + 20 * local_fmt_ratio) / 2
        )

    # 6. 计算总分
    llm_score = llm_result.get('score', 0)
    type_score = calculate_total_score(question_type, merged_scores)

    # 如果 LLM 给的总分和融合计算的总分差距超过 15 分，取平均值
    if abs(llm_score - type_score) > 15:
        final_score = round((llm_score + type_score) / 2, 1)
    else:
        # 以 LLM 总分为准，但做上下限修正
        final_score = _clamp(llm_score, 0, 100)

    # 7. 构建最终结果
    result = {
        'score': final_score,
        'dimension_scores': merged_scores,
        'hit_points': llm_result.get('hit_points', []),
        'missing_points': llm_result.get('missing_points', []),
        'ai_feedback': llm_result.get('ai_feedback', ''),
        'improving_suggestions': llm_result.get('improving_suggestions', []),
        'question_type': question_type,
        'local_checks': local_checks,
        'from_cache': False,
    }

    # 题型特有字段
    if question_type == 'zonghe':
        result['logic_chain_analysis'] = llm_result.get('logic_chain_analysis', {})
    if question_type == 'duice':
        result['countermeasures'] = llm_result.get('countermeasures', [])
        result['generic_countermeasures'] = llm_result.get('generic_countermeasures', [])
        result['problem_accuracy'] = llm_result.get('problem_accuracy', '')
    if question_type == 'zhixing':
        result['format_check'] = llm_result.get('format_check', {})
        result['content_check'] = llm_result.get('content_check', {})
    if question_type == 'zuowen':
        result['tier'] = llm_result.get('tier', '')
        result['tier_reason'] = llm_result.get('tier_reason', '')
        result['thesis_analysis'] = llm_result.get('thesis_analysis', {})
        result['argument_analysis'] = llm_result.get('argument_analysis', {})
        result['structure_analysis'] = llm_result.get('structure_analysis', {})
        result['bonus_points'] = llm_result.get('bonus_points', [])
        result['penalty_points'] = llm_result.get('penalty_points', [])

    # 8. 缓存结果
    grader_cache.set(pid, qid, user_answer, result)

    return result


def grade_answer_legacy(pid: str, qid: str, question: dict,
                        user_answer: str, material: list = None) -> dict:
    """批改答案（旧版通用评分，保持向后兼容）

    使用旧版的五维度评分体系，不区分题型。
    """
    cached = grader_cache.get(pid, qid, user_answer)
    if cached:
        cached['from_cache'] = True
        return cached

    messages = build_grading_prompt(question, user_answer, material)

    try:
        result = call_llm(messages)
        result['from_cache'] = False

        # 使用旧版维度计算做校验
        hit_points = result.get('hit_points', [])
        missing_points = result.get('missing_points', [])
        local_dims = calculate_dimensions(question, user_answer, hit_points, missing_points)

        # 将 LLM 返回的中文维度名映射到本地
        llm_dims = result.get('dimension_scores', {})
        dim_mapping = {
            '踩点命中': 'point_coverage',
            '逻辑结构': 'logic_structure',
            '语言规范': 'language',
            '字数控制': 'word_count',
            '卷面整洁': 'format'
        }

        # 如果 LLM 返回的是中文维度名，转换为英文
        if any(k in dim_mapping for k in llm_dims):
            converted = {}
            for cn_key, en_key in dim_mapping.items():
                if cn_key in llm_dims:
                    converted[en_key] = llm_dims[cn_key]
            result['dimension_scores'] = converted

        grader_cache.set(pid, qid, user_answer, result)
        return result

    except Exception as e:
        raise Exception(f"批改失败: {str(e)}")


def get_simple_feedback(question: dict, user_answer: str) -> str:
    """获取简化反馈（免费用户）

    Args:
        question: 题目信息
        user_answer: 考生答案

    Returns:
        简要评价文本
    """
    prompt = build_simple_feedback_prompt(question, user_answer)
    try:
        messages = [
            {"role": "system", "content": "你是一位申论老师，请简要评价学生答案。"},
            {"role": "user", "content": prompt}
        ]
        return call_llm(messages, parse_json=False)
    except Exception as e:
        logger.error(f"简化反馈生成失败: {e}")
        return "答案已提交。由于服务繁忙，详细批改将在稍后完成。"
