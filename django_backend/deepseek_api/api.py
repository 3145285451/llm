from ninja import NinjaAPI, Router
from django.http import (
    HttpRequest,
    StreamingHttpResponse,
)  # (新增) 导入 StreamingHttpResponse
from typing import Optional, Generator  # (新增) 导入 Generator
from . import services
from django.conf import settings
from .schemas import LoginIn, LoginOut, ChatIn, ChatOut, HistoryOut, ErrorResponse
from .models import APIKey
from .services import (
    get_or_create_session,
    deepseek_r1_api_call,
    # (移除) get_cached_reply, (流式响应不能缓存)
    # (移除) set_cached_reply, (流式响应不能缓存)
)
from datetime import datetime
import logging
import re  # (修复) 导入 re
import time  # (新增) 导入 time
import json  # (新增) 导入 json

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


# (修改) chat 接口
@router.post("/chat")  # (修改) 移除 response 定义
def chat(request, data: ChatIn):
    # (修改) 使用 SSE 格式 (text/event-stream)
    if not request.auth:
        return StreamingHttpResponse(
            "data: "
            + json.dumps({"type": "error", "chunk": "请先登录获取API Key"})
            + "\n\n",
            status=401,
            content_type="text/event-stream",
        )

    session_id = data.session_id.strip() or "default_session"
    user_input = data.user_input.strip()
    if not user_input:
        return StreamingHttpResponse(
            "data: "
            + json.dumps({"type": "error", "chunk": "请输入消息内容"})
            + "\n\n",
            status=400,
            content_type="text/event-stream",
        )

    user = request.auth
    session = get_or_create_session(session_id, user)
    conversation_history = session.get_conversation_history()

    # (新增) 定义流式生成器 (后端解析)
    def stream_generator() -> Generator[str, None, None]:
        buffer = ""
        is_thinking = False
        full_clean_reply = ""  # 用于最后存入数据库
        duration = 0.0

        try:
            # (修改) 迭代 services.py 中的流
            for raw_chunk in deepseek_r1_api_call(user_input, conversation_history):
                print(raw_chunk)
                # (新增) 检查 services.py 发来的特殊元数据块
                if raw_chunk.startswith("[METADATA_CHUNK]:"):
                    try:
                        metadata_json = raw_chunk.split(":", 1)[1]
                        metadata = json.loads(metadata_json)
                        if metadata.get("type") == "metadata":
                            duration = metadata.get("duration", 0.0)
                            # (修改) 发送最终的元数据事件
                            yield "data: " + json.dumps(
                                {"type": "metadata", "duration": duration}
                            ) + "\n\n"
                    except Exception as e:
                        logger.warning(f"解析元数据块失败: {e}")
                    continue  # 停止迭代

                buffer += raw_chunk

                # (*** 关键修复 ***)
                # 循环处理缓冲区，直到缓冲区被清空或需要更多数据
                while True:
                    if not is_thinking:
                        # 1. 尝试查找 <think> 开始
                        start_index = buffer.find("<think>")
                        if start_index != -1:
                            # 找到了
                            before = buffer[:start_index]
                            if before:
                                yield "data: " + json.dumps(
                                    {"type": "content", "chunk": before}
                                ) + "\n\n"
                                full_clean_reply += before

                            buffer = buffer[start_index + len("<think>") :]
                            is_thinking = True
                            # (修复) 继续循环，立即处理 <think> 后的内容
                            continue
                        else:
                            # [!!! 修复 !!!]
                            # 没找到 <think>，意味着整个缓冲区都是 content
                            # yield 它，然后清空缓冲区，等待下一个 chunk
                            if buffer:
                                yield "data: " + json.dumps(
                                    {"type": "content", "chunk": buffer}
                                ) + "\n\n"
                                full_clean_reply += buffer
                                buffer = ""
                            break  # 退出 while 循环，等待下一个 raw_chunk

                    if is_thinking:
                        # 2. 尝试查找 </think> 结束
                        end_index = buffer.find("</think>")
                        if end_index != -1:
                            # 找到了
                            think_chunk = buffer[:end_index]
                            if think_chunk:
                                yield "data: " + json.dumps(
                                    {"type": "think", "chunk": think_chunk}
                                ) + "\n\n"

                            buffer = buffer[end_index + len("</think>") :]
                            is_thinking = False
                            # (修复) 继续循环，立即处理 </think> 后的内容
                            continue
                        else:
                            # 没找到结束标签，意味着整个缓冲区都是 think
                            if buffer:
                                yield "data: " + json.dumps(
                                    {"type": "think", "chunk": buffer}
                                ) + "\n\n"
                                buffer = ""
                            break  # 退出 while 循环，等待下一个 raw_chunk

                    # (修复) 如果代码执行到这里，意味着在一次循环中
                    # 既处理了 <ctrl3347> 又处理了 </think>，
                    # 应该继续循环检查剩余的 buffer

            # (循环结束) 处理剩余缓冲区
            if is_thinking and buffer:
                # 不太可能发生，但作为保险
                yield "data: " + json.dumps(
                    {"type": "think", "chunk": buffer}
                ) + "\n\n"
            elif buffer:
                yield "data: " + json.dumps(
                    {"type": "content", "chunk": buffer}
                ) + "\n\n"
                full_clean_reply += buffer

            # (新增) 流全部结束后，更新数据库
            try:
                # (修复) 确保只保存清理后的回复
                # (clean_llm_reply 再次调用以防万一，但 full_clean_reply 应该是对的)
                final_save = clean_llm_reply(full_clean_reply)
                session.update_context(user_input, final_save.strip())
                logger.info(f"会话 {session_id} 已更新 (用户: {user.user})")
            except Exception as e:
                logger.error(f"数据库上下文更新失败: {e}")

        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            yield "data: " + json.dumps(
                {"type": "error", "chunk": f"流处理失败: {e}"}
            ) + "\n\n"

    # (修改) 返回 StreamingHttpResponse
    response = StreamingHttpResponse(
        stream_generator(), content_type="text/event-stream"  # (修改) SSE
    )
    # (新增) 禁用 Nginx 缓冲
    response["X-Accel-Buffering"] = "no"
    return response


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
