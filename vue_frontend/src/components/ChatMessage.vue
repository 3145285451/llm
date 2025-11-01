<template>
  <div class="message" :class="{ 'user-message': isUser }">
    <div class="message-avatar">
      <div :class="isUser ? 'user-avatar' : 'bot-avatar'">
        {{ isUser ? '用户' : 'AI' }}
      </div>
    </div>
    <div class="message-content">
      
      <!-- (新增) 深度思考模块 -->
      <div 
        v-if="!isUser && thinkProcess" 
        class="think-container"
      >
        <div 
          class="think-header" 
          @click="showthinkProcess = !showthinkProcess"
        >
          <div class="think-title">
            <brain-icon class="icon" />
            <!-- (修改) 文本从“深度思考中...”改为动态显示 -->
            <span>{{ showthinkProcess ? '隐藏思考过程' : '查看思考过程' }}</span>
          </div>
          <div class="think-meta">
            <!-- (修改) 增加“思考”二字，更明确 -->
            <span>思考耗时: {{ duration }}s</span>
            <chevron-down 
              v-if="!showthinkProcess" 
              class="icon chevron"
            />
            <chevron-up 
              v-else 
              class="icon chevron"
            />
          </div>
        </div>
        <!-- (新增) 可折叠内容 -->
        <div 
          v-if="showthinkProcess" 
          class="think-content" 
          v-html="renderedthinkProcess"
        >
        </div>
      </div>

      <!-- 最终回复 -->
      <div v-if="isUser" class="message-text">
        {{ content }}
      </div>
      <div v-else class="message-text" v-html="renderedMarkdown">
      </div>

      <!-- 时间戳 -->
      <div class="message-time">
        {{ formatTime(timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineProps, ref } from 'vue'; // (修改) 导入 ref
import { marked } from 'marked'; // 导入 marked 库
import { BrainIcon, ChevronDownIcon, ChevronUpIcon } from 'vue-tabler-icons'; // (新增) 导入图标

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
  },
  // (新增) 深度思考 props
  thinkProcess: {
    type: String,
    default: null
  },
  duration: {
    type: Number,
    default: null
  }
});

// (新增) 折叠状态
const showthinkProcess = ref(false);

// 计算属性，用于解析 AI 的 Markdown 回复
const renderedMarkdown = computed(() => {
  if (props.isUser) {
    return props.content; 
  }
  return marked.parse(props.content || '', {
    gfm: true,
    breaks: true,
    headerIds: false,
    mangle: false,
  });
});

// (新增) 计算属性，用于解析 AI 的思考过程
const renderedthinkProcess = computed(() => {
  if (!props.thinkProcess) {
    return '';
  }
  // 使用 marked 解析 Markdown
  return marked.parse(props.thinkProcess || '', {
    gfm: true,
    breaks: true,
    headerIds: false,
    mangle: false,
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
  flex-shrink: 0;
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

/* (修改) 调整 .message-content padding */
.message-content {
  padding: 0; /* (修改) 移除 padding */
  border-radius: var(--radius);
  position: relative;
  width: 100%; /* (新增) 确保占满宽度 */
}

.message:not(.user-message) .message-content {
  background-color: var(--bot-message);
}

.user-message .message-content {
  background-color: var(--user-message);
  padding: 0.75rem 1rem; /* (恢复) 用户消息不受影响 */
}

/* (修改) .message-text (最终回复) 现在需要自己的 padding */
.message-text {
  padding: 0.75rem 1rem;
  margin-bottom: 0.25rem;
  line-height: 1.5;
  /* v-html 内容是动态插入的，'scoped' 样式无法应用到它们。
    我们将在全局的 styles.css 中为 .message-text 里的
    p, ul, ol, pre, code, blockquote 等元素添加样式。
  */
}

.user-message .message-text {
  padding: 0; /* (恢复) 用户消息的 text 也不受影响 */
  white-space: pre-wrap;
}

/* (修改) 时间戳也需要 padding */
.message-time {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-align: right;
  padding: 0 1rem 0.5rem; /* (新增 padding) */
}

.user-message .message-time {
  padding: 0; /* (恢复) 用户消息不受影响 */
}


/* (新增) 深度思考模块样式 */
.think-container {
  background-color: rgba(0, 0, 0, 0.03); /* 嵌套在气泡内，颜色稍暗 */
  border-bottom: 1px solid var(--border-color);
  /* 移除顶部圆角，因为它在顶部 */
  border-top-left-radius: var(--radius);
  border-top-right-radius: var(--radius);
}

.think-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem; /* (修改) 匹配气泡 padding */
  cursor: pointer;
  user-select: none;
}

.think-header:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.think-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.think-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0; /* (新增) 防止图标被压缩 */
}

.chevron {
  transition: transform 0.2s ease;
}

.think-content {
  padding: 0.75rem 1rem; /* (修改) 匹配气泡 padding */
  background-color: rgba(255, 255, 255, 0.5); /* 稍亮的背景 */
  
  /* (新增) 确保 v-html 渲染的内容样式正确 */
  /* 使用 :deep() 为 v-html 内容设置样式 */
}

/* (新增) :deep() 样式，用于 v-html 渲染的思考过程 */
:deep(.think-content p) {
  margin-bottom: 0.5rem;
}
:deep(.think-content p:last-child) {
  margin-bottom: 0;
}
:deep(.think-content ul),
:deep(.think-content ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.5rem;
}
:deep(.think-content li) {
  margin-bottom: 0.25rem;
}
:deep(.think-content code) {
  background-color: var(--border-color);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
}
:deep(.think-content strong) {
  font-weight: 600;
}
</style>
