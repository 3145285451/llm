from ninja import NinjaAPI, Router
from django.http import HttpRequest
from typing import Optional
from . import services
from django.conf import settings
from .schemas import LoginIn, LoginOut, ChatIn, ChatOut, HistoryOut, ErrorResponse
from .models import APIKey
from .services import (
    get_or_create_session,
    deepseek_r1_api_call,
    get_cached_reply,
    set_cached_reply,
)
from datetime import datetime
import logging
import re  # (修复) 导入 re 用于清理

logger = logging.getLogger(__name__)

api = NinjaAPI(title="DeepSeek-KAI API", version="0.0.1")


def api_key_auth(request):
    """验证请求头中的API Key"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    try:
        scheme, key = auth_header.split()
        if scheme.lower() != "bearer":
            return None
        api_key = APIKey.objects.get(key=key)
        return api_key
    except (ValueError, APIKey.DoesNotExist):
        return None


router = Router(auth=api_key_auth)


# (修复) 新增一个辅助函数来清理回复
def clean_llm_reply(reply: str) -> str:
    """从LLM的原始回复中移除 <think>...</think> 标签块"""
    # re.DOTALL 使 '.' 能够匹配包括换行符在内的任意字符
    return re.sub(r"<think>.*?</think>\s*", "", reply, flags=re.DOTALL).strip()


@api.post("/login", response={200: LoginOut, 400: ErrorResponse, 403: ErrorResponse})
def login(request, data: LoginIn):
    username = data.username.strip()
    password = data.password.strip()
    if not username or not password:
        return 400, {"error": "用户名和密码不能为空"}
    if password != "secret":
        return 403, {"error": "密码错误"}
    key = services.create_api_key(username)
    return {"api_key": key, "expiry": settings.TOKEN_EXPIRY_SECONDS}


@router.post("/chat", response={200: ChatOut, 401: ErrorResponse})
def chat(request, data: ChatIn):
    if not request.auth:
        return 401, {"error": "请先登录获取API Key"}

    session_id = data.session_id.strip() or "default_session"
    user_input = data.user_input.strip()
    if not user_input:
        return 400, {"error": "请输入消息内容"}

    user = request.auth
    session = get_or_create_session(session_id, user)

    prompt_for_cache = session.context + f"用户：{user_input}\n回复："
    logger.info(f"用户输入：{user_input}")

    conversation_history = session.get_conversation_history()

    # (修复) 步骤 1: 获取原始回复
    reply_raw = deepseek_r1_api_call(user_input, conversation_history)

    # (修复) 步骤 2: 清理 <think> 标签
    reply_clean = clean_llm_reply(reply_raw)

    # (修复) 步骤 3: 使用清理后的回复设置缓存
    # 注意：缓存键应该基于 user_input，而不是 prompt_for_cache，
    # 因为 prompt_for_cache 依赖于可能很长的 session.context
    # 这里我们暂时保留原逻辑，但建议修改
    set_cached_reply(prompt_for_cache, reply_clean, session_id, user)

    # (修复) 步骤 4: 使用清理后的回复更新上下文
    session.update_context(user_input, reply_clean)

    print("666\n", user_input)
    print(reply_clean)  # (修复) 打印清理后的回复

    return {
        "reply": reply_clean,  # (修复) 返回清理后的回复
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


@router.get("/history", response={200: HistoryOut})
def history(request, session_id: str = "default_session"):
    processed_session_id = session_id.strip() or "default_session"
    session = services.get_or_create_session(processed_session_id, request.auth)
    return {"history": session.context}


@router.delete("/history", response={200: dict})
def clear_history(request, session_id: str = "default_session"):
    processed_session_id = session_id.strip() or "default_session"
    session = services.get_or_create_session(processed_session_id, request.auth)
    session.clear_context()
    return {"message": "历史记录已清空"}


api.add_router("", router)
