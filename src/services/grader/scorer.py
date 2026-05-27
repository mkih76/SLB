import json
from src.services.grader.cache import grader_cache
from src.services.grader.prompts import build_grading_prompt, build_simple_feedback_prompt
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS


def call_llm(messages: list, parse_json: bool = True):
    """调用LLM API

    Args:
        messages: 聊天消息列表
        parse_json: 是否将响应内容解析为JSON，默认True
    """
    import requests

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}"
    }

    data = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS
    }

    try:
        response = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        if parse_json:
            return json.loads(content)
        return content
    except Exception as e:
        raise Exception(f"LLM调用失败: {str(e)}")


def grade_answer(pid: str, qid: str, question: dict, user_answer: str, material: list = None) -> dict:
    """批改答案"""
    # Check cache
    cached = grader_cache.get(pid, qid, user_answer)
    if cached:
        cached['from_cache'] = True
        return cached

    # Build prompt and call LLM
    messages = build_grading_prompt(question, user_answer, material)

    try:
        result = call_llm(messages)
        result['from_cache'] = False

        # Cache the result
        grader_cache.set(pid, qid, user_answer, result)

        return result
    except Exception as e:
        raise Exception(f"批改失败: {str(e)}")


def get_simple_feedback(question: dict, user_answer: str) -> str:
    """获取简化反馈（免费用户）"""
    prompt = build_simple_feedback_prompt(question, user_answer)
    try:
        messages = [
            {"role": "system", "content": "你是一位申论老师，请简要评价学生答案。"},
            {"role": "user", "content": prompt}
        ]
        return call_llm(messages, parse_json=False)
    except Exception:
        return "答案已提交。由于服务繁忙，详细批改将在稍后完成。"
