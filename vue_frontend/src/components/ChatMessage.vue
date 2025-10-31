<template>
  <div class="message" :class="{ 'user-message': isUser }">
    <div class="message-avatar">
      <div :class="isUser ? 'user-avatar' : 'bot-avatar'">
        {{ isUser ? '用户' : 'AI' }}
      </div>
    </div>
    <div class="message-content">
      <!-- 
        安全更新：
        - 用户消息 (isUser: true) 使用 {{ content }} 纯文本插值，防止 XSS。
        - AI 消息 (isUser: false) 使用 v-html 渲染 Markdown 解析后的 HTML。
      -->
      <div v-if="isUser" class="message-text">
        {{ content }}
      </div>
      <div v-else class="message-text" v-html="renderedMarkdown">
      </div>

      <div class="message-time">
        {{ formatTime(timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineProps } from 'vue';
import { marked } from 'marked'; // 导入 marked 库

const props = defineProps({
  isUser: {
    type: Boolean,
    required: true
  },
  content: {
    type: String,
    required: true
  },
  timestamp: {
    type: Date,
    required: true
  }
});

// 计算属性，用于解析 AI 的 Markdown 回复
const renderedMarkdown = computed(() => {
  if (props.isUser) {
    return props.content; // 理论上不会执行，因为 v-if="isUser" 已处理
  }
  // 使用 marked 解析 Markdown
  return marked.parse(props.content || '', {
    gfm: true,      // 启用 GitHub Flavored Markdown
    breaks: true,   // 将单个换行符渲染为 <br>
    headerIds: false, // 不生成 header id
    mangle: false,    // 不混淆 email
  });
});

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString();
};
</script>

<style scoped>
.message {
  display: flex;
  margin-bottom: 1rem;
  max-width: 80%;
}

.message.user-message {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message-avatar {
  margin-right: 0.5rem;
}

.user-message .message-avatar {
  margin-right: 0;
  margin-left: 0.5rem;
}

.user-avatar, .bot-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
  font-size: 0.875rem;
}

.user-avatar {
  background-color: var(--primary-color);
  color: white;
}

.bot-avatar {
  background-color: var(--secondary-color);
  color: white;
}

.message-content {
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  position: relative;
}

.message:not(.user-message) .message-content {
  background-color: var(--bot-message);
}

.user-message .message-content {
  background-color: var(--user-message);
}

.message-text {
  margin-bottom: 0.25rem;
  line-height: 1.5;
  /* v-html 内容是动态插入的，'scoped' 样式无法应用到它们。
    我们将在全局的 styles.css 中为 .message-text 里的
    p, ul, ol, pre, code, blockquote 等元素添加样式。
  */
}

.user-message .message-text {
  /* 对于用户的纯文本消息，我们希望保留换行符。
    v-if="isUser" 使用 {{ content }} 会丢失换行，
    所以我们用 white-space: pre-wrap 来保留它们。
  */
  white-space: pre-wrap;
}

.message-time {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-align: right;
}
</style>
