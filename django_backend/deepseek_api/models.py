from django.db import models
from django.db.models import F
import string
import random
import time
import logging
logger = logging.getLogger(__name__)

from django.db.models import indexes

class APIKey(models.Model):
    key = models.CharField(max_length=32, unique=True)
    user = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_time = models.IntegerField()  # 过期时间戳
    
    @classmethod
    def generate_key(cls, length=32):
        """生成随机 API Key"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def is_valid(self):
        """检查 API Key 是否未过期"""
        return time.time() < self.expiry_time
    
    def __str__(self):
        return f"{self.user} - {self.key}"


class RateLimit(models.Model):
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE,
                                db_index=True, to_field='key', related_name='rate_limits')
    count = models.IntegerField(default=0)
    reset_time = models.IntegerField()  # 重置时间戳

    class Meta:
        indexes = [
            models.Index(fields=['api_key', 'reset_time'])
        ]
    
    def should_limit(self, max_requests, interval):
        """检查是否应该限制请求"""
        current_time = time.time()
        if current_time > self.reset_time:
            self.count = 0
            self.reset_time = current_time + interval
            self.save()
            return False
        return self.count >= max_requests


class ConversationSession(models.Model):
    session_id = models.CharField(max_length=100)
    # 正确的外键定义：关联 APIKey 的 id（默认）
    user = models.ForeignKey(
        APIKey, 
        on_delete=models.CASCADE, 
        related_name='sessions'
    )
    context = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('session_id', 'user')  # 确保用户+会话ID唯一
    
    def update_context(self, user_input, bot_reply):
        """原子更新上下文，避免并发覆盖"""
        new_entry = f"用户：{user_input}\n回复：{bot_reply}\n"
        # 数据库层面拼接，而非内存中
        ConversationSession.objects.filter(
            pk=self.pk,  # 精确匹配当前会话
            user=self.user  # 确保用户一致
        ).update(context=F('context') + new_entry)
        # 刷新实例，获取更新后的值
        self.refresh_from_db()

        # import logging
        # logger = logging.getLogger(__name__)
        # logger.info(f"更新会话 {self.session_id}（用户：{self.user.key}）：{new_entry}")
    
    def clear_context(self):
        """清空对话上下文"""
        self.context = ""
        self.save()
    
    def get_conversation_history(self):
        """
        将上下文解析为结构化的对话历史列表
        返回格式: [{'role': 'user', 'content': 'xxx'}, {'role': 'assistant', 'content': 'yyy'}]
        """
        history = []
        if not self.context:
            return history
            
        lines = self.context.strip().split('\n')
        i = 0
        while i < len(lines):
            if lines[i].startswith('用户：'):
                user_msg = lines[i][3:]  # 去掉"用户："前缀
                i += 1
                if i < len(lines) and lines[i].startswith('回复：'):
                    assistant_msg = lines[i][3:]  # 去掉"回复："前缀
                    history.append({'role': 'user', 'content': user_msg})
                    history.append({'role': 'assistant', 'content': assistant_msg})
                    i += 1
                else:
                    history.append({'role': 'user', 'content': user_msg})
            else:
                i += 1
        return history    
    def __str__(self):
        return self.session_id
