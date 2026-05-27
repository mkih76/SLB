# 本地规则检测模块
#
# 提供字数检测、口语化检测、格式检测、万能对策检测、逻辑链检测等功能
# 与 LLM 批改结果融合，提升批改准确性

import re


# ============================================================
# 分题型维度权重定义
# ============================================================

QUESTION_TYPE_DIMENSIONS = {
    "guina": {  # 归纳概括
        "point_coverage": 0.70,
        "conciseness": 0.15,
        "accuracy": 0.10,
        "format": 0.05
    },
    "zonghe": {  # 综合分析
        "logic_chain": 0.30,
        "point_coverage": 0.30,
        "depth": 0.20,
        "language": 0.10,
        "format": 0.10
    },
    "duice": {  # 提出对策
        "problem_identification": 0.20,
        "targeting": 0.25,
        "feasibility": 0.25,
        "specificity": 0.20,
        "format": 0.10
    },
    "zhixing": {  # 贯彻执行
        "format_correctness": 0.20,
        "purpose_achievement": 0.25,
        "content_completeness": 0.30,
        "language_appropriateness": 0.15,
        "word_count": 0.10
    },
    "zuowen": {  # 大作文
        "thesis_accuracy": 0.25,
        "argument_richness": 0.25,
        "structure": 0.20,
        "language": 0.20,
        "innovation": 0.10
    }
}

# 兼容旧版的通用维度权重（用于未指定题型时的兜底）
LEGACY_DIMENSIONS = {
    "point_coverage": 0.40,
    "logic_structure": 0.25,
    "language": 0.20,
    "word_count": 0.10,
    "format": 0.05
}


# ============================================================
# 字数检测
# ============================================================

def count_chinese_chars(text):
    """统计中文字符数（不含标点）"""
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def calculate_word_count_score(answer: str, word_limit: str) -> tuple:
    """计算字数得分

    支持格式：'150-200字'、'不少于800字'、'1000字左右'
    返回 (得分比例0-1, 说明文字)
    """
    if not word_limit:
        return 1.0, "字数未指定"

    chars = count_chinese_chars(answer)

    # 格式1: "150-200字"
    range_match = re.search(r'(\d+)-(\d+)字', word_limit)
    if range_match:
        min_words = int(range_match.group(1))
        max_words = int(range_match.group(2))
        if min_words <= chars <= max_words:
            return 1.0, f"字数符合要求（{chars}字）"
        elif chars < min_words:
            ratio = chars / min_words if min_words > 0 else 0
            return ratio, f"字数不足（{chars}字），要求至少{min_words}字"
        else:
            over_ratio = (chars - max_words) / max_words if max_words > 0 else 0
            ratio = max(0.5, 1 - over_ratio * 0.5)
            return ratio, f"字数超出（{chars}字），要求不超过{max_words}字"

    # 格式2: "不少于800字"
    min_match = re.search(r'不少于(\d+)字', word_limit)
    if min_match:
        min_words = int(min_match.group(1))
        if chars >= min_words:
            return 1.0, f"字数符合要求（{chars}字）"
        else:
            ratio = chars / min_words if min_words > 0 else 0
            return ratio, f"字数不足（{chars}字），要求不少于{min_words}字"

    # 格式3: "1000字左右"
    around_match = re.search(r'(\d+)字左右', word_limit)
    if around_match:
        target = int(around_match.group(1))
        deviation = abs(chars - target) / target if target > 0 else 0
        if deviation <= 0.1:
            return 1.0, f"字数符合要求（{chars}字）"
        else:
            ratio = max(0.5, 1 - deviation)
            return ratio, f"字数偏差较大（{chars}字），目标约{target}字"

    # 兜底：尝试提取数字
    num_match = re.search(r'(\d+)', word_limit)
    if num_match:
        target = int(num_match.group(1))
        if chars >= target:
            return 1.0, f"字数符合要求（{chars}字）"
        else:
            ratio = chars / target if target > 0 else 0
            return ratio, f"字数不足（{chars}字），要求{target}字"

    return 1.0, f"字数要求格式无法识别（{word_limit}）"


# ============================================================
# 口语化检测
# ============================================================

COLLOQUIAL_PATTERNS = [
    # 第一人称口语
    r'我觉得', r'我认为', r'我想\b', r'在我看来',
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
    '统筹推进', '着力构建', '深入推进', '全面加强',
    '坚持问题导向', '坚持系统观念', '坚持底线思维',
    '以人民为中心', '新发展理念', '高质量发展',
    '治理体系和治理能力现代化', '共建共治共享',
    '放管服改革', '供给侧结构性改革',
    '绿水青山就是金山银山',
    '乡村振兴战略', '新型城镇化',
    '基层社会治理', '网格化管理',
    '数字政府', '智慧城市',
    '稳中求进', '统筹发展和安全',
    '新发展格局', '中国式现代化',
]


def detect_colloquial(text):
    """检测口语化表达，返回问题列表"""
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
    """检测是否使用了申论规范用语，返回匹配列表"""
    found = []
    for phrase in FORMAL_PHRASES:
        if phrase in text:
            found.append(phrase)
    return found


def calculate_language_score(text, max_score=20):
    """计算语言规范得分

    Args:
        text: 考生答案
        max_score: 该维度满分（默认20）

    Returns:
        得分（0-max_score）
    """
    score = max_score

    # 口语化扣分
    colloquial = detect_colloquial(text)
    for issue in colloquial:
        score -= issue['count'] * 2
        if score < 0:
            score = 0
            break

    # 规范用语加分（但不超过满分）
    formal = detect_formal_language(text)
    score = min(max_score, score + len(formal) * 1)

    return max(0, min(max_score, score))


# ============================================================
# 格式检测（贯彻执行题专用）
# ============================================================

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
        "title_patterns": [r'.*'],
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
    },
    "简报": {
        "required": ["title", "main_body"],
        "optional": [],
        "title_patterns": [r'关于.*的简报', r'简报', r'工作简报'],
        "structure": ["situation", "practice", "result"]
    }
}


def check_document_format(text, doc_type):
    """检查文档格式是否符合文种要求

    Args:
        text: 考生答案
        doc_type: 文种名称（如"讲话稿"、"倡议书"）

    Returns:
        dict: {
            'score_ratio': 0-1的得分比例,
            'checks': {'has_title': bool, ...},
            'issues': ['问题描述']
        }
    """
    rules = DOCUMENT_FORMAT_RULES.get(doc_type)
    if not rules:
        return {'score_ratio': 1.0, 'checks': {}, 'issues': []}

    issues = []
    checks = {}
    required = rules.get('required', [])
    met_count = 0

    lines = text.strip().split('\n')
    first_line = lines[0].strip() if lines else ''

    # 检查标题
    if rules.get('no_title'):
        checks['has_title'] = False
        met_count += 1
    elif 'title' in required:
        has_title = False
        for pattern in rules.get('title_patterns', []):
            if re.search(pattern, first_line):
                has_title = True
                break
        checks['has_title'] = has_title
        if has_title:
            met_count += 1
        else:
            issues.append('缺少标题或标题格式不正确')

    # 检查称谓
    if rules.get('no_salutation'):
        checks['has_salutation'] = False
        met_count += 1
    elif 'salutation' in required:
        has_salutation = False
        for pattern in rules.get('salutation_patterns', []):
            if re.search(pattern, text[:300]):
                has_salutation = True
                break
        checks['has_salutation'] = has_salutation
        if has_salutation:
            met_count += 1
        else:
            issues.append('缺少称谓')

    # 检查落款
    if 'signature' in required:
        has_signature = False
        for pattern in rules.get('signature_patterns', []):
            if re.search(pattern, text[-300:]):
                has_signature = True
                break
        checks['has_signature'] = has_signature
        if has_signature:
            met_count += 1
        else:
            issues.append('缺少落款')

    # 其他必需项默认算作已满足（需要 LLM 进一步判断）
    other_required = [r for r in required
                      if r not in ['title', 'salutation', 'signature']]
    met_count += len(other_required)

    total_required = len(required)
    score_ratio = met_count / total_required if total_required > 0 else 1.0

    return {
        'score_ratio': score_ratio,
        'checks': checks,
        'issues': issues
    }


# ============================================================
# 万能对策检测（提出对策题专用）
# ============================================================

GENERIC_COUNTERMEASURES = [
    '加强宣传教育', '加大宣传力度', '完善法律法规', '加强制度建设',
    '健全体制机制', '加强组织领导', '加大资金投入', '加强监督考核',
    '建立长效机制', '提高思想认识', '强化责任落实', '营造良好氛围',
    '加强协调配合', '加大处罚力度', '严格执法',
]

GENERIC_PATTERNS = [
    r'加强.*教育', r'加大.*力度', r'完善.*制度',
    r'健全.*机制', r'提高.*认识', r'强化.*落实',
    r'营造.*氛围',
]


def detect_generic_countermeasures(text):
    """检测万能对策

    Args:
        text: 考生答案

    Returns:
        list: [{'content': '匹配到的万能对策', 'type': 'exact_match/pattern_match'}]
    """
    found = []
    seen = set()

    # 精确匹配
    for gc in GENERIC_COUNTERMEASURES:
        if gc in text and gc not in seen:
            found.append({'content': gc, 'type': 'exact_match'})
            seen.add(gc)

    # 模式匹配
    for pattern in GENERIC_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in seen:
                found.append({'content': match, 'type': 'pattern_match'})
                seen.add(match)

    return found


def check_countermeasure_quality(countermeasure_text):
    """检查单条对策的质量

    Args:
        countermeasure_text: 单条对策文本

    Returns:
        dict: {
            'score': 0-100的质量分,
            'has_subject': 是否有执行主体,
            'has_action': 是否有具体操作,
            'has_effect': 是否有预期效果,
            'is_generic': 是否为万能对策,
            'feedback': ['问题描述']
        }
    """
    score = 100
    feedback = []

    # 检查是否万能对策
    generic = detect_generic_countermeasures(countermeasure_text)
    if generic:
        score -= 40
        feedback.append('包含万能对策表述，缺少具体性')

    # 检查是否有执行主体
    subject_patterns = [r'政府', r'企业', r'社区', r'学校', r'医院',
                        r'部门', r'机构', r'组织', r'单位', r'基层']
    has_subject = any(re.search(p, countermeasure_text) for p in subject_patterns)
    if not has_subject:
        score -= 20
        feedback.append('缺少明确的执行主体')

    # 检查是否有具体操作
    action_patterns = [r'通过', r'采取', r'实施', r'推行', r'建立',
                       r'设立', r'开展', r'推动', r'引导', r'鼓励']
    has_action = any(re.search(p, countermeasure_text) for p in action_patterns)
    if not has_action:
        score -= 20
        feedback.append('缺少具体的操作手段')

    # 检查是否有预期效果
    effect_patterns = [r'从而', r'进而', r'以此', r'以便', r'促进',
                       r'推动', r'实现', r'提升', r'改善']
    has_effect = any(re.search(p, countermeasure_text) for p in effect_patterns)
    if not has_effect:
        score -= 10
        feedback.append('缺少预期效果描述')

    return {
        'score': max(0, score),
        'has_subject': has_subject,
        'has_action': has_action,
        'has_effect': has_effect,
        'is_generic': len(generic) > 0,
        'feedback': feedback
    }


# ============================================================
# 逻辑链检测（综合分析题专用）
# ============================================================

def detect_logic_chain(text):
    """检测综合分析题的逻辑链完整性

    Args:
        text: 考生答案

    Returns:
        dict: {
            'has_thesis': 是否有总论点句,
            'has_what': 是否有"是什么"层次,
            'has_why': 是否有"为什么"层次,
            'has_how': 是否有"怎么办"层次,
            'has_conclusion': 是否有总结升华,
            'chain_breaks': ['断裂描述'],
            'completeness': 0-1的完整度
        }
    """
    result = {
        'has_thesis': False,
        'has_what': False,
        'has_why': False,
        'has_how': False,
        'has_conclusion': False,
        'chain_breaks': [],
        'completeness': 0.0
    }

    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    if not paragraphs:
        return result

    # 检测总论点句（通常在第一段）
    thesis_patterns = [r'这表明', r'这说明', r'由此可见', r'因此.*是',
                       r'本质上', r'核心在于', r'关键在于']
    first_para = paragraphs[0]
    result['has_thesis'] = any(re.search(p, first_para) for p in thesis_patterns)

    # 检测"是什么"层次
    what_patterns = [r'是指', r'即', r'所谓', r'本质上', r'具体来说',
                     r'表现为', r'主要体现在', r'一方面']
    result['has_what'] = any(
        any(re.search(p, para) for p in what_patterns)
        for para in paragraphs
    )

    # 检测"为什么"层次
    why_patterns = [r'原因', r'因为', r'由于', r'根源', r'导致',
                    r'之所以', r'影响', r'意义', r'重要性']
    result['has_why'] = any(
        any(re.search(p, para) for p in why_patterns)
        for para in paragraphs
    )

    # 检测"怎么办"层次
    how_patterns = [r'应该', r'需要', r'必须', r'建议', r'对策',
                    r'措施', r'路径', r'关键在于', r'着力']
    result['has_how'] = any(
        any(re.search(p, para) for p in how_patterns)
        for para in paragraphs
    )

    # 检测总结句（通常在最后一段）
    last_para = paragraphs[-1]
    conclusion_patterns = [r'总之', r'综上', r'因此', r'只有.*才能',
                           r'唯有', r'让我们', r'方能']
    result['has_conclusion'] = any(
        re.search(p, last_para) for p in conclusion_patterns
    )

    # 检测逻辑链断裂
    if result['has_what'] and not result['has_why']:
        result['chain_breaks'].append('有"是什么"但缺少"为什么"分析')
    if result['has_why'] and not result['has_how']:
        result['chain_breaks'].append('有"为什么"但缺少"怎么办"对策')
    if not result['has_thesis'] and not result['has_conclusion']:
        result['chain_breaks'].append('缺少总论点句和总结句')

    # 计算完整度
    elements = [result['has_thesis'], result['has_what'],
                result['has_why'], result['has_how'], result['has_conclusion']]
    result['completeness'] = sum(elements) / len(elements)

    return result


# ============================================================
# 结构检测（通用）
# ============================================================

def calculate_structure_score(answer: str) -> int:
    """计算逻辑结构得分（通用版，用于旧接口兼容）

    Returns:
        得分（0-25）
    """
    score = 0

    # 序数词标记
    structure_markers = ['第一', '第二', '第三', '首先', '其次', '最后',
                         '一是', '二是', '三是', '一方面', '另一方面']
    for marker in structure_markers:
        if marker in answer:
            score += 5
            break

    # 段落数
    paras = [p for p in answer.split('\n') if p.strip()]
    if 2 <= len(paras) <= 5:
        score += 10
    elif len(paras) > 5:
        score += 5

    # 过渡词
    transition_words = ['因此', '但是', '然而', '总之', '综上所述',
                        '与此同时', '不仅如此', '更重要的是']
    for tw in transition_words:
        if tw in answer:
            score += 5
            break

    return min(25, score)


# ============================================================
# 卷面整洁检测
# ============================================================

def calculate_format_score(answer: str) -> tuple:
    """计算卷面整洁得分

    Returns:
        (得分0-5, 说明文字)
    """
    score = 5

    # 标点符号密度过高
    punct_count = len(re.findall(r'[，。；、：""''（）]', answer))
    if punct_count > len(answer) * 0.3:
        score -= 1

    # 不规范符号
    if '...' in answer or '～' in answer:
        score -= 1

    return max(0, score), "卷面基本整洁"


# ============================================================
# 综合维度计算（兼容旧接口）
# ============================================================

def calculate_dimensions(question: dict, user_answer: str,
                         hit_points: list, missing_points: list) -> dict:
    """计算各维度得分（兼容旧版接口）

    该函数保持与旧版 scorer.py 的向后兼容性，
    返回旧版的五维度格式。新版分题型评分请使用 calculate_type_dimensions。

    Args:
        question: 题目信息
        user_answer: 考生答案
        hit_points: 命中的要点列表
        missing_points: 遗漏的要点列表

    Returns:
        dict: {"踩点命中": score, "逻辑结构": score, ...}
    """
    word_limit = question.get('word_limit', '')

    word_ratio, _ = calculate_word_count_score(user_answer, word_limit)
    word_score = int(10 * word_ratio)

    format_score, _ = calculate_format_score(user_answer)
    structure_score = calculate_structure_score(user_answer)

    key_points = question.get('key_points', [])
    hit_rate = len(hit_points) / max(len(key_points), 1)
    hit_score = int(40 * hit_rate)

    language_score = calculate_language_score(user_answer, max_score=14)

    return {
        "踩点命中": hit_score,
        "逻辑结构": structure_score,
        "语言规范": language_score,
        "字数控制": word_score,
        "卷面整洁": format_score
    }


# ============================================================
# 分题型综合计算（新版）
# ============================================================

def calculate_type_dimensions(question_type: str, question: dict,
                               user_answer: str, llm_scores: dict) -> dict:
    """计算分题型的综合维度得分

    融合本地规则检测结果和 LLM 返回的分数。

    Args:
        question_type: 题型代码（guina/zonghe/duice/zhixing/zuowen）
        question: 题目信息
        user_answer: 考生答案
        llm_scores: LLM 返回的维度分数

    Returns:
        dict: 融合后的维度分数
    """
    dimensions = QUESTION_TYPE_DIMENSIONS.get(question_type, LEGACY_DIMENSIONS)
    local_checks = {}
    merged = {}

    # 本地检测
    word_limit = question.get('word_limit', '')
    word_ratio, word_comment = calculate_word_count_score(user_answer, word_limit)
    local_checks['word_count'] = {'ratio': word_ratio, 'comment': word_comment}

    colloquial = detect_colloquial(user_answer)
    local_checks['colloquial'] = colloquial

    formal = detect_formal_language(user_answer)
    local_checks['formal_count'] = len(formal)

    # 题型特定检测
    if question_type == 'zhixing':
        doc_type = question.get('document_type', '讲话稿')
        local_checks['format'] = check_document_format(user_answer, doc_type)

    if question_type == 'duice':
        local_checks['generic'] = detect_generic_countermeasures(user_answer)

    if question_type == 'zonghe':
        local_checks['logic_chain'] = detect_logic_chain(user_answer)

    # 融合分数
    for dim, weight in dimensions.items():
        llm_val = llm_scores.get(dim)

        if dim == 'word_count':
            # 字数以本地为准
            if question_type == 'zhixing':
                max_val = int(weight * 100)
                merged[dim] = int(max_val * word_ratio)
            elif llm_val is not None:
                merged[dim] = llm_val
            else:
                merged[dim] = int(10 * word_ratio)

        elif dim == 'format' and question_type == 'zhixing':
            # 贯彻执行的格式以本地为准
            fmt = local_checks.get('format', {})
            max_val = int(weight * 100)
            merged[dim] = int(max_val * fmt.get('score_ratio', 1.0))

        elif dim == 'language' or dim == 'language_appropriateness':
            # 语言：本地口语化扣分 + LLM评估
            local_lang = calculate_language_score(user_answer, max_score=int(weight * 100))
            if llm_val is not None:
                colloquial_penalty = len(colloquial) * 2
                merged[dim] = max(0, min(int(weight * 100), llm_val - colloquial_penalty))
            else:
                merged[dim] = local_lang

        else:
            # 其他维度以 LLM 为准
            merged[dim] = llm_val if llm_val is not None else 0

    return merged


def calculate_total_score(question_type: str, dimension_scores: dict) -> float:
    """根据维度分数计算总分

    Args:
        question_type: 题型代码
        dimension_scores: 维度分数字典

    Returns:
        总分（0-100）
    """
    dimensions = QUESTION_TYPE_DIMENSIONS.get(question_type, LEGACY_DIMENSIONS)
    total = 0.0

    for dim, weight in dimensions.items():
        score = dimension_scores.get(dim, 0)
        max_for_dim = int(weight * 100)
        if max_for_dim > 0:
            total += (score / max_for_dim) * weight * 100

    return round(total, 1)
