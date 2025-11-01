import time
import threading
from typing import Dict, Any, Optional, List
from django.core.cache import cache
import hashlib
from .models import APIKey, RateLimit, ConversationSession
from django.conf import settings
from topklogsystem import TopKLogSystem  # (修改) 导入
import logging

logger = logging.getLogger(__name__)

# (修改) 全局初始化 TopKLogSystem
# 避免在每次API调用时都重新加载索引，极大提高效率
try:
    log_system = TopKLogSystem(
        log_path="./data/log", llm="deepseek-r1:7b", embedding_model="bge-large:latest"
    )
    logger.info("TopKLogSystem 全局初始化成功。")
except Exception as e:
    log_system = None
    logger.error(f"TopKLogSystem 全局初始化失败: {e}")

# 全局配置
# API_KEY_LENGTH = 32
# TOKEN_EXPIRY_SECONDS = 3600
# RATE_LIMIT_MAX = 5  # 每分钟最大请求数
# RATE_LIMIT_INTERVAL = 60

# 线程锁用于速率限制
rate_lock = threading.Lock()


# (修改) 更新 deepseek_r1_api_call
def deepseek_r1_api_call(prompt: str, conversation_history: List[Dict] = None) -> str:
    """
    调用 DeepSeek-R1 API 函数。
    (修改) 现在分别传递 'prompt' (当前查询) 和 'conversation_history' (历史)
    """

    if log_system is None:
        logger.error("Log system 未初始化，返回错误。")
        return "错误：日志分析系统未成功初始化。"

    # (修改) 使用全局的 log_system 实例
    # (修改) 调用更新后的 query 方法，该方法接受 history
    print("conversation_history\n", conversation_history)
    result = log_system.query(prompt, history=conversation_history)

    time.sleep(0.5)  # 保留原始延迟

    # print(result["response"]) # (保留)
    return result["response"]


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


# def get_or_create_session(session_id: str, user: APIKey) -> ConversationSession:
# """获取或创建会话，关联当前用户（通过API Key）"""
# session, created = ConversationSession.objects.get_or_create(
# session_id=session_id,
# user=user,  # 绑定用户
# defaults={'context': ''}
# )
# return session


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
    # 调试日志：确认是否创建新会话（created=True 表示新会话）
    # import logging
    # logger = logging.getLogger(__name__)
    logger.info(
        f"会话 {session_id}（用户：{user.user}）{'创建新会话' if created else '加载旧会话'}"
    )
    return session


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
