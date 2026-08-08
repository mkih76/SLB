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
    import time as _time

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

    # 端点可能间歇性不可用：最多重试 2 次，指数退避
    max_retries = 2
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{llm['base_url']}/chat/completions",
                headers=headers,
                json=data,
                timeout=90
            )
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message'].get('content') or ''
            # 推理模型（如 deepseek-v4-flash）可能把正文放 reasoning_content，
            # 或 max_tokens 不够导致 content 为空——回退读取
            if not content.strip():
                reasoning = result['choices'][0]['message'].get('reasoning_content') or ''
                # reasoning 里通常只有思考过程，无法作为正式输出；抛出明确错误
                if reasoning:
                    raise Exception(f"LLM 返回内容为空（推理型模型 max_tokens 不足）: {reasoning[:200]}")
                raise Exception("LLM 返回内容为空")
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
            last_err = e
            logger.warning(f"LLM 调用失败 (第{attempt+1}次): {e}")
            if attempt < max_retries:
                _time.sleep(2 * (attempt + 1))  # 2s, 4s 退避
            else:
                break
    raise Exception(f"LLM调用失败: {str(last_err)}")


def _clamp(value, min_val, max_val):
    """将值限制在指定范围内"""
    return max(min_val, min(max_val, value))


def _grade_local_fallback(question: dict, user_answer: str, material: list = None) -> dict:
    """本地规则降级批改（LLM 不可用时兜底，不依赖外部 API）

    基于题目采分点做关键词匹配，结合字数/口语化/格式等本地检测，
    输出与 LLM 版结构一致的批改结果。
    """
    import re
    qtype = question.get('type', 'guina')
    key_points = question.get('key_points') or []
    word_limit = question.get('word_limit') or ''

    # 1. 采分点匹配（关键词 + 别名）
    hit_points = []
    missing_points = []
    answer = user_answer or ''
    if not key_points:
        # 无采分点（自定义题）：退化为字数/结构粗评
        char_count = count_chinese_chars(answer)
        dim_scores_en = {}
        total = _clamp(round(char_count / 300 * 60, 1) + 20, 0, 100)
        return {
            'score': total,
            'dimension_scores': dim_scores_en,
            'hit_points': [],
            'missing_points': [],
            'ai_feedback': '（AI 服务暂不可用，本次为本地规则评分）作答已收到，请结合材料完善要点。',
            'improving_suggestions': ['题目暂无标准采分点，建议对照参考答案自查要点覆盖度。'],
            'local_fallback': True,
        }

    for kp in key_points:
        if not isinstance(kp, dict):
            continue
        point = kp.get('point', '')
        score = kp.get('score', 0)
        aliases = kp.get('alias') or []
        # 要点正文或别名任一命中即算得分
        keywords = [point] + list(aliases)
        matched = False
        for kw in keywords:
            if kw and kw in answer:
                matched = True
                break
        if matched:
            hit_points.append({'point': point, 'score': score, 'matched': True})
        else:
            missing_points.append({'point': point})

    # 2. 维度分数（本地规则，键名与 LLM 版一致）
    try:
        dim_scores = calculate_dimensions(question, answer, hit_points, missing_points)
        # 转换为英文键名（新版 scorer 用英文维度）
        dim_map = {'踩点命中': 'point_coverage', '逻辑结构': 'logic_structure',
                   '语言规范': 'language', '字数控制': 'word_count', '卷面整洁': 'format'}
        dim_scores_en = {dim_map.get(k, k): v for k, v in dim_scores.items()}
        total = calculate_total_score(qtype, dim_scores_en)
    except Exception:
        # 极端兜底：按命中率粗算
        total = round(100 * len(hit_points) / max(len(key_points), 1), 1)
        dim_scores_en = {}

    # 3. 本地反馈文案
    hit_rate = len(hit_points) / max(len(key_points), 1)
    if hit_rate >= 0.8:
        verdict = '整体作答较好，要点覆盖全面。'
    elif hit_rate >= 0.5:
        verdict = '作答基本合格，但存在要点遗漏。'
    elif hit_rate >= 0.3:
        verdict = '作答要点覆盖不足，需要加强审题与踩点。'
    else:
        verdict = '作答与采分点差距较大，建议结合材料分点作答。'

    suggestions = []
    if missing_points:
        suggestions.append('以下要点未命中：' + '、'.join(p['point'] for p in missing_points[:5]))
    colloquial = detect_colloquial(answer)
    if colloquial:
        suggestions.append('答案存在口语化表达：' + '、'.join(colloquial[:3]) + '，建议改用规范书面语。')
    char_count = count_chinese_chars(answer)
    if char_count < 80:
        suggestions.append('作答字数偏少（约%d字），建议充分展开论述。' % char_count)
    if not suggestions:
        suggestions.append('继续保持分点作答结构，注意结合材料佐证。')

    return {
        'score': total,
        'dimension_scores': dim_scores_en,
        'hit_points': hit_points,
        'missing_points': missing_points,
        'ai_feedback': verdict + '（AI 服务暂不可用，本次为本地规则评分）',
        'improving_suggestions': suggestions,
        'local_fallback': True,
    }


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


def grade_answer_local(pid: str, qid: str, question: dict,
                       user_answer: str, material: list = None) -> dict:
    """纯本地规则批改（不调用 LLM，供降级兜底使用）"""
    result = _grade_local_fallback(question, user_answer, material)
    result['pid'] = pid
    result['qid'] = qid
    return result


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
        logger.warning(f"LLM 批改失败，使用本地规则降级 (pid={pid}, qid={qid}): {e}")
        llm_result = _grade_local_fallback(question, user_answer, material)

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
