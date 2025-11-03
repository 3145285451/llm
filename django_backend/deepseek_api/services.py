import time
import threading
from typing import Dict, Any, Optional, List
from django.core.cache import cache
import hashlib
from .models import APIKey, RateLimit, ConversationSession
from django.conf import settings
from topklogsystem import TopKLogSystem
import logging
import json
from ddgs import DDGS

logger = logging.getLogger(__name__)

# 全局初始化 TopKLogSystem
# 使用 DeepSeek-R1:7B 作为主模型，bge-large:latest 作为嵌入模型
# 避免在每次API调用时都重新加载索引，极大提高效率
try:
    log_system = TopKLogSystem(
        log_path="./data/log",
        llm="deepseek-r1:7b",  # DeepSeek-R1:7B - 基于 Qwen2 架构，支持思考过程 (thinking)
        embedding_model="bge-large:latest",  # BGE-Large 嵌入模型，用于向量检索
    )
    logger.info("TopKLogSystem 全局初始化成功。使用模型: DeepSeek-R1:7B")
except Exception as e:
    log_system = None
    logger.error(f"TopKLogSystem 全局初始化失败: {e}")


def real_web_search(query: str, max_results: int = 3) -> List[Dict]:
    logger.info(f"[REAL-WEB-SEARCH] 正在执行联网搜索: {query}")
    try:
        # 使用 DDGS 上下文管理器
        with DDGS() as ddgs:
            results = ddgs.text(query,region="cn-zh",backend='yandex',max_results=max_results)
            
            if not results:
                logger.warning(f"联网搜索 '{query}' 没有返回结果。")
                return []
            
            # 将结果格式化为
            # List[{"content": "摘要", "source": "链接"}]
            formatted_results = [
                {"content": r['body'], "source": r['href']} 
                for r in results
            ]
            return formatted_results
    except Exception as e:
        # 处理可能的网络或 API 异常
        logger.error(f"DuckDuckGo 搜索失败: {e}")
        return []


def deepseek_r1_api_call(
    prompt: str, 
    conversation_history: List[Dict] = None,
    use_db_search: bool = True,
    use_web_search: bool = False
):
    """
    调用 DeepSeek-R1:7B 模型 API 函数 - 流式响应。
    ... (函数文档保持不变) ...
    """

    if log_system is None:
        logger.error("Log system 未初始化，返回错误。")
        yield "错误：日志分析系统未成功初始化。"
        return

    try:
        # (新增) 步骤 1: 根据标志获取上下文
        log_results = []
        web_results = []

        if use_db_search:
            logger.info(f"执行数据库日志检索: {prompt}")
            log_results = log_system.retrieve_logs(prompt, top_k=5) 
        
        if use_web_search:
            logger.info(f"执行联网搜索: {prompt}")
            # [修改] 调用真实的搜索函数，而不是 mock
            web_results = real_web_search(prompt, max_results=10)
            
        # (新增) 步骤 2: 准备组合上下文
        combined_context = {
            "log_context": log_results,
            "web_context": web_results
        }
        
        # (修改) 步骤 3: 调用 generate_response
        for chunk in log_system.generate_response(
            prompt, 
            context=combined_context, 
            history=conversation_history
        ):
            yield chunk 
            
    except Exception as e:
        logger.error(f"deepseek_r1_api_call 流式处理失败: {e}")
        yield f"API 调用失败: {e}"


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

# (删除) check_rate_limit 函数在当前版本中未被 api.py 调用，暂时省略
# ... (如果需要，可以保留 check_rate_limit 函数) ...
# (保留) 为了代码完整性，保留 check_rate_limit
rate_lock = threading.Lock() # 确保在顶部添加了 threading
def check_rate_limit(key_str: str) -> bool:
    """检查 API Key 的请求频率是否超过限制"""
    with rate_lock:
        try:
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
