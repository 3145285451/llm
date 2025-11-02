import time
import threading
from typing import Dict, Any, Optional, List
from django.core.cache import cache
import hashlib
from .models import APIKey, RateLimit, ConversationSession
from django.conf import settings
from topklogsystem import TopKLogSystem  # (修改) 导入
import logging
import json  # (新增) 导入 json

logger = logging.getLogger(__name__)

# 全局初始化 TopKLogSystem
# 使用 DeepSeek-R1:7B 作为主模型，bge-large:latest 作为嵌入模型
# 避免在每次API调用时都重新加载索引，极大提高效率
try:
    log_system = TopKLogSystem(
        log_path="./data/log", 
        llm="deepseek-r1:7b",  # DeepSeek-R1:7B - 基于 Qwen2 架构，支持思考过程 (thinking)
        embedding_model="bge-large:latest"  # BGE-Large 嵌入模型，用于向量检索
    )
    logger.info("TopKLogSystem 全局初始化成功。使用模型: DeepSeek-R1:7B")
except Exception as e:
    log_system = None
    logger.error(f"TopKLogSystem 全局初始化失败: {e}")

# ... (rate_lock)


def deepseek_r1_api_call(
    prompt: str, conversation_history: List[Dict] = None
):  # -> Generator[str, None, None]
    """
    调用 DeepSeek-R1:7B 模型 API 函数 - 流式响应。
    
    模型信息:
    - 模型名称: deepseek-r1:7b
    - 架构: 基于 Qwen2 架构的 DeepSeek-R1 模型
    - 参数量: 7.6B
    - 上下文长度: 131072 tokens
    - 特性: 支持思考过程 (thinking)，使用 <think> 标签
    
    返回: 原始文本块的生成器，包含 <think> 标签的思考过程
    """

    if log_system is None:
        logger.error("Log system 未初始化，返回错误。")
        yield "错误：日志分析系统未成功初始化。"
        return

    # (修改) 移除 start_time 计时

    try:
        # (修改) 简单地迭代 log_system.query
        for chunk in log_system.query(prompt, history=conversation_history):
            yield chunk  # (修改) yield 原始块
    except Exception as e:
        logger.error(f"deepseek_r1_api_call 流式处理失败: {e}")
        yield f"API 调用失败: {e}"

    # (修改) 移除所有计时和 [METADATA_CHUNK] 逻辑
    # 流在此处自然结束


def create_api_key(username: str) -> str:
    """
    为用户创建或更新 API Key。
    如果用户已存在，则更新其 key 和过期时间。
    否则，创建新记录。
    """
    expiry_duration = settings.TOKEN_EXPIRY_SECONDS
    expiry_timestamp = int(time.time()) + expiry_duration

    # 尝试获取用户，如果不存在则创建
    api_key_obj, created = APIKey.objects.update_or_create(
        user=username,
        defaults={
            "key": APIKey.generate_key(),
            "expiry_time": expiry_timestamp,
        },
    )
    return api_key_obj.key


def validate_api_key(key_str: str) -> bool:
    """验证 API Key 是否存在且未过期"""
    try:
        api_key = APIKey.objects.get(key=key_str)
        if api_key.is_valid():
            return True
        else:
            api_key.delete()  # 删除过期key
            return False
    except APIKey.DoesNotExist:
        return False


def check_rate_limit(key_str: str) -> bool:
    """检查 API Key 的请求频率是否超过限制"""
    with rate_lock:
        try:
            # api_key = APIKey.objects.get(key=key_str)
            # rate_limit = RateLimit.objects.get(api_key=api_key)
            rate_limit = RateLimit.objects.select_related("api_key").get(
                api_key__key=key_str
            )

            current_time = time.time()
            if current_time > rate_limit.reset_time:
                rate_limit.count = 1
                rate_limit.reset_time = current_time + settings.RATE_LIMIT_INTERVAL
                rate_limit.save()
                return True
            elif rate_limit.count < settings.RATE_LIMIT_MAX:
                rate_limit.count += 1
                rate_limit.save()
                return True
            else:
                return False
        except RateLimit.DoesNotExist:
            # 如果速率限制记录不存在，创建一个新的
            try:
                current_time = time.time()
                api_key = APIKey.objects.get(key=key_str)
                RateLimit.objects.create(
                    api_key=api_key,
                    count=1,
                    reset_time=current_time + settings.RATE_LIMIT_INTERVAL,
                )
                return True
            except APIKey.DoesNotExist:
                return False


# ... (get_or_create_session 不变)
def get_or_create_session(session_id: str, user: APIKey) -> ConversationSession:
    """
    获取或创建用户的专属会话：
    - 若用户+session_id已存在 → 加载旧会话（保留历史）
    - 若不存在 → 创建新会话（空历史）
    """
    session, created = ConversationSession.objects.get_or_create(
        session_id=session_id,  # 匹配会话ID
        user=user,  # 匹配当前用户（关键！避免跨用户会话冲突）
        defaults={"context": ""},
    )
    logger.info(
        f"会话 {session_id}（用户：{user.user}）{'创建新会话' if created else '加载旧会话'}"
    )
    return session


# (注意：流式 API 不再使用缓存)
def get_cached_reply(prompt: str, session_id: str, user: APIKey) -> str | None:
    """缓存键包含 session_id 和 user，避免跨会话冲突"""
    cache_key = f"reply:{user.user}:{session_id}:{hash(prompt)}"
    return cache.get(cache_key)


def set_cached_reply(
    prompt: str, reply: str, session_id: str, user: APIKey, timeout=3600
):
    cache_key = f"reply:{user.user}:{session_id}:{hash(prompt)}"
    cache.set(cache_key, reply, timeout)


def generate_cache_key(original_key: str) -> str:
    """
    生成安全的缓存键。
    对原始字符串进行哈希处理，确保键长度固定且仅包含安全字符。
    """
    # 使用SHA256哈希函数生成固定长度的键（64位十六进制字符串）
    hash_obj = hashlib.sha256(original_key.encode("utf-8"))
    return hash_obj.hexdigest()
