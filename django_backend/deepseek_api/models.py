from django.db import models
from django.db.models import F
import string
import random
import time
import logging
from django.db.models.functions import Concat
from django.db.models import Value
import re

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
        return "".join(random.choice(characters) for _ in range(length))

    def is_valid(self):
        """检查 API Key 是否未过期"""
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
    reset_time = models.IntegerField()  # 重置时间戳

    class Meta:
        indexes = [models.Index(fields=["api_key", "reset_time"])]

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
    user = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name="sessions")
    context = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("session_id", "user")  # 确保用户+会话ID唯一

    def update_context(self, user_input, bot_reply):
        """
        原子更新上下文。
        [修复] 检查当前上下文，如果为空或格式错误（垃圾数据），则重写；否则追加。
        """
        new_entry = f"用户：{user_input}\n回复：{bot_reply}\n"

        # 获取当前上下文并去除首尾空白
        current_context = self.context.strip()

        if not current_context:
            # 1. 如果 context 为空 (或只包含空白)，我们执行重写 (Overwrite)
            ConversationSession.objects.filter(pk=self.pk, user=self.user).update(
                context=new_entry
            )
            logger.info(
                f"[重写] 会话 {self.session_id}（用户：{self.user.key}）：{new_entry}"
            )
        else:
            # 2. 如果 context 不为空，我们执行追加 (Concat)
            # 注意：如果 context 包含垃圾数据，这里仍会追加。
            # 一个更健壮的检查是 current_context.startswith("用户：")
            # 但为简单起见，我们假设非空即有效。
            # [修改为更健壮的检查]
            if not current_context.startswith("用户："):
                # 3. 如果 context 非空，但不以 "用户：" 开头，视为垃圾数据，执行重写
                ConversationSession.objects.filter(pk=self.pk, user=self.user).update(
                    context=new_entry
                )
                logger.warning(
                    f"[重写-垃圾数据] 会话 {self.session_id}（用户：{self.user.key}）：{new_entry}"
                )
            else:
                # 4. Context 非空且格式正确，执行追加
                ConversationSession.objects.filter(pk=self.pk, user=self.user).update(
                    context=Concat("context", Value(new_entry))
                )
                logger.info(
                    f"[追加] 更新会话 {self.session_id}（用户：{self.user.key}）：{new_entry}"
                )

        # 刷新实例，获取更新后的值
        self.refresh_from_db()

        # import logging # (确保 logging 已经在本文件顶部导入)
        # logger = logging.getLogger(__name__) # (确保 logger 已经在本文件顶部定义)

        # [修改]：取消这一行的注释
        # logger.info(f"更新会话 {self.session_id}（用户：{self.user.key}）：{new_entry}") # 这一行在原始代码中是重复的，已合并到上面的逻辑中

    def clear_context(self):
        """清空对话上下文"""
        self.context = ""
        self.save()

    def get_conversation_history(self):
        """
        [修复] 将上下文解析为结构化的对话历史列表
        使用正则表达式处理多行回复
        返回格式: [{'role': 'user', 'content': 'xxx'}, {'role': 'assistant', 'content': 'yyy'}]
        """
        history = []
        if not self.context:
            return history

        # 使用正则表达式（前瞻断言）按 "用户：" 分割，保留 "用户："
        # 这样每个 'part' 都是一个 "用户：... \n回复：..." 块
        parts = re.split(r"(?=用户：)", self.context.strip())

        for part in parts:
            part_stripped = part.strip()
            if not part_stripped:
                continue

            # 按 "\n回复：" 分割用户和助手内容 (最多只分一次)
            # 这样可以确保回复中的 \n 被保留
            qa_split = re.split(r"\n回复：", part_stripped, maxsplit=1)

            if len(qa_split) >= 1 and qa_split[0].startswith("用户："):
                # 提取用户内容 (去掉 "用户：" 前缀)
                user_content = qa_split[0][3:].strip()
                history.append({"role": "user", "content": user_content})

                # 如果存在回复内容
                if len(qa_split) == 2:
                    assistant_content = qa_split[1].strip()
                    history.append({"role": "assistant", "content": assistant_content})

        return history

    def __str__(self):
        return self.session_id
