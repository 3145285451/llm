from ninja import NinjaAPI, Router
from django.http import HttpRequest, StreamingHttpResponse
from typing import Optional, Generator 
from . import services
from django.conf import settings
from .schemas import LoginIn, LoginOut, ChatIn, ChatOut, HistoryOut, ErrorResponse
from .models import APIKey
from .services import get_or_create_session, deepseek_r1_api_call
from datetime import datetime
import logging
import re
import time
import json

logger = logging.getLogger(__name__)

api = NinjaAPI(title="DeepSeek-R1:7B API", version="0.0.1")


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


def clean_llm_reply(reply: str) -> str:
    """
    从 DeepSeek-R1:7B 的原始回复中移除 <think>...</think> 标签块

    DeepSeek-R1 模型的思考过程被包裹在 <think> 标签中，
    此函数用于清理这些思考过程，只保留最终的用户可见回复。
    """
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


@router.post("/chat")  
def chat(request, data: ChatIn):
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

    if data.context and len(data.context) > 0:
        # 情况A：前端提供了 context，使用它作为对话历史
        logger.info(
            f"使用前端提供的 context (会话: {session_id}, 上下文长度: {len(data.context)})"
        )
        history_for_llm = data.context
        is_regeneration = False  # 前端已经处理了截断，不需要重新生成检测
    else:
        # 情况B：前端没有提供 context，回退到从数据库加载历史
        conversation_history = session.get_conversation_history()
        print(conversation_history)
        history_for_llm = conversation_history
        is_regeneration = False

        if (
            len(conversation_history) >= 2
            and conversation_history[-1]["role"] == "assistant"
            and conversation_history[-2]["role"] == "user"
            and conversation_history[-2]["content"] == user_input
        ):

            logger.info(f"检测到重新生成 (会话: {session_id})")
            history_for_llm = conversation_history[:-2]
            is_regeneration = True

        elif (
            len(conversation_history) >= 1
            and conversation_history[-1]["role"] == "user"
            and conversation_history[-1]["content"] == user_input
        ):

            logger.info(f"检测到对失败消息的重新生成 (会话: {session_id})")
            history_for_llm = conversation_history[:-1]  # 移除 Q_last
            is_regeneration = True

    def stream_generator() -> Generator[str, None, None]:
        buffer = ""
        is_thinking = False
        full_clean_reply = ""  # 用于最后存入数据库

        start_time = time.time()  # 在开始迭代前计时
        think_time_sent = False  # 确保元数据只发送一次

        try:
            for raw_chunk in deepseek_r1_api_call(user_input, history_for_llm):
                buffer += raw_chunk

                while True:
                    if not is_thinking:
                        start_index = buffer.find("<think>")
                        if start_index != -1:
                            before = buffer[:start_index]
                            if before:
                                yield "data: " + json.dumps(
                                    {"type": "content", "chunk": before}
                                ) + "\n\n"
                                full_clean_reply += before
                            buffer = buffer[start_index + len("<think>") :]
                            is_thinking = True
                            continue
                        else:
                            if buffer:
                                yield "data: " + json.dumps(
                                    {"type": "content", "chunk": buffer}
                                ) + "\n\n"
                                full_clean_reply += buffer
                                buffer = ""
                            break
                    if is_thinking:
                        end_index = buffer.find("</think>")
                        if end_index != -1:
                            if not think_time_sent:
                                end_think_time = time.time()
                                duration = round(end_think_time - start_time, 2)
                                yield "data: " + json.dumps(
                                    {"type": "metadata", "duration": duration}
                                ) + "\n\n"
                                think_time_sent = True

                            think_chunk = buffer[:end_index]
                            if think_chunk:
                                yield "data: " + json.dumps(
                                    {"type": "think", "chunk": think_chunk}
                                ) + "\n\n"

                            buffer = buffer[end_index + len("</think>") :]
                            is_thinking = False
                            continue
                        else:
                            if buffer:
                                yield "data: " + json.dumps(
                                    {"type": "think", "chunk": buffer}
                                ) + "\n\n"
                                buffer = ""
                            break

            # (循环结束) 处理剩余缓冲区
            if is_thinking and buffer:
                yield "data: " + json.dumps({"type": "think", "chunk": buffer}) + "\n\n"
            elif buffer:
                yield "data: " + json.dumps(
                    {"type": "content", "chunk": buffer}
                ) + "\n\n"
                full_clean_reply += buffer

            # 流全部结束后，更新数据库
            try:
                final_save = clean_llm_reply(full_clean_reply).strip()

                # 检查是否使用了前端提供的 context（编辑模式）
                if data.context and len(data.context) > 0:
                    # 编辑模式：前端已经截断了历史，我们需要重写整个上下文
                    # 格式化为 "\n用户：{q}\n回复：{a}\n" 格式
                    new_context_str = ""
                    # 添加前端提供的截断后的历史
                    for msg in history_for_llm:
                        if msg["role"] == "user":
                            new_context_str += f"\n用户：{msg['content']}\n"
                        elif msg["role"] == "assistant":
                            new_context_str += f"\n回复：{msg['content']}\n"

                    # 添加当前轮次的新回复（编辑后的提问 + 新的 AI 回答）
                    new_context_str += f"\n用户：{user_input}\n"
                    new_context_str += f"\n回复：{final_save}\n"

                    # 重写数据库上下文
                    session.context = new_context_str.strip()
                    session.save()
                    logger.info(
                        f"编辑模式：会话 {session_id} 已更新 (用户: {user.user})"
                    )

                elif is_regeneration:

                    new_context_str = ""
                    # 重新组合截断的历史
                    for msg in history_for_llm:
                        if msg["role"] == "user":
                            new_context_str += f"\n用户：{msg['content']}\n"
                        elif msg["role"] == "assistant":
                            new_context_str += f"\n回复：{msg['content']}\n"

                    # 添加当前轮次的新回复
                    new_context_str += f"\n用户：{user_input}\n"
                    new_context_str += f"\n回复：{final_save}\n"

                    # (假设 session.context 是可写的)
                    session.context = new_context_str.strip()
                    session.save()

                else:
                    # 正常追加 (调用 models.py 中的方法)
                    session.update_context(user_input, final_save)


                logger.info(f"会话 {session_id} 已更新 (用户: {user.user})")
            except Exception as e:
                logger.error(f"数据库上下文更新失败: {e}")

        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            yield "data: " + json.dumps(
                {"type": "error", "chunk": f"流处理失败: {e}"}
            ) + "\n\n"

    #返回 StreamingHttpResponse
    response = StreamingHttpResponse(
        stream_generator(), content_type="text/event-stream"  # (修改) SSE
    )
    # 禁用 Nginx 缓冲
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
