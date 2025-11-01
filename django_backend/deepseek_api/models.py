from django.db import models
from django.db.models import F, Value
from django.db.models.functions import (
    Concat,
    Coalesce,
)
import string
import random
import time
import logging
import re  # (修复) 导入 re

logger = logging.getLogger(__name__)

from django.db.models import indexes


class APIKey(models.Model):
    key = models.CharField(max_length=32, unique=True)
    user = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_time = models.IntegerField()

    @classmethod
    def generate_key(cls, length=32):
        characters = string.ascii_letters + string.digits
        return "".join(random.choice(characters) for _ in range(length))

    def is_valid(self):
        return time.time() < self.expiry_time

    def __str__(self):
        return f"{self.user} - {self.key}"


class RateLimit(models.Model):
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.CASCADE,
        db_index=True,
        to_field="key",
        related_name="rate_limits",
    )
    count = models.IntegerField(default=0)
    reset_time = models.IntegerField()

    class Meta:
        indexes = [models.Index(fields=["api_key", "reset_time"])]

    def should_limit(self, max_requests, interval):
        current_time = time.time()
        if current_time > self.reset_time:
            self.count = 0
            self.reset_time = current_time + interval
            self.save()
            return False
        return self.count >= max_requests


class ConversationSession(models.Model):
    session_id = models.CharField(max_length=100)
    user = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name="sessions")
    context = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("session_id", "user")

    def update_context(self, user_input, bot_reply):
        new_entry = f"用户：{user_input}\n回复：{bot_reply}\n"
        ConversationSession.objects.filter(pk=self.pk, user=self.user).update(
            context=Concat(
                Coalesce("context", Value("")),
                Value(new_entry),
            )
        )
        self.refresh_from_db()

    def clear_context(self):
        self.context = ""
        self.save()

    # (修复) 重写 get_conversation_history 以支持多行
    def get_conversation_history(self):
        """
        (修复版) 将上下文解析为结构化的对话历史列表
        (新版：可以正确处理多行回复)
        返回格式: [{'role': 'user', 'content': 'xxx'}, {'role': 'assistant', 'content': 'yyy'}]
        """
        history = []
        if not self.context:
            return history

        # 使用 "用户：" 作为分隔符，来切分每一轮对话
        # filter(None, ...) 会移除切分后可能产生的空字符串（比如开头就是"用户："）
        turns = filter(None, self.context.strip().split("用户："))

        for turn_text in turns:
            # 每一轮对话现在都以用户输入开头，
            # 并可能包含 "回复："

            # 使用 "回复：" 来分割用户输入和助手回复
            # maxsplit=1 确保只在第一个 "回复：" 处分割
            parts = turn_text.split("回复：", 1)

            user_msg = parts[0].strip()
            if user_msg:
                history.append({"role": "user", "content": user_msg})

            if len(parts) > 1:
                # parts[1] 包含从 "回复：" 之后到下一个 "用户：" 之前的所有内容
                assistant_msg = parts[1].strip()

                # (双重保险) 再次清理 <think> 标签，以防数据库中存有旧的脏数据
                assistant_msg_clean = re.sub(
                    r"<think>.*?</think>\s*", "", assistant_msg, flags=re.DOTALL
                ).strip()

                if assistant_msg_clean:
                    history.append(
                        {"role": "assistant", "content": assistant_msg_clean}
                    )
                # (移除 else) 如果清理后为空，就不添加了

        return history

    def __str__(self):
        return self.session_id
