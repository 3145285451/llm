<template>
  <div class="message" :class="{ 'user-message': isUser }">
    <div class="message-avatar">
      <div :class="isUser ? 'user-avatar' : 'bot-avatar'">
        {{ isUser ? '用户' : 'AI' }}
      </div>
    </div>
    <div class="message-content">
      
      <!-- (新增) 点赞提示 -->
      <div v-if="showLikeToast" class="feedback-toast like">
        感谢您的支持！
      </div>

      <!-- (新增) 点踩弹窗 -->
      <div v-if="showDislikeModal" class="feedback-modal-overlay">
        <div class="feedback-modal">
          <p>感谢您的反馈，已提交至工作人员。是否需要重新生成回答？</p>
          <div class="feedback-modal-actions">
            <button class="secondary" @click="closeDislikeModal">取消</button>
            <button class="primary" @click="handleDislikeRegenerate">
              <refresh-icon class="icon-small-inline" />
              重新生成
            </button>
          </div>
        </div>
      </div>
      
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
            <span>{{ showthinkProcess ? '隐藏思考过程' : '查看思考过程' }}</span>
          </div>
          <div class="think-meta">
            <span>思考耗时: {{ displayTime }}s</span>
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
        <div 
          v-if="showthinkProcess" 
          class="think-content" 
          v-html="renderedthinkProcess"
        >
        </div>
      </div>

      <div v-if="isUser" class="message-text">
        {{ content }}
      </div>
      <div v-else class="message-text" v-html="renderedMarkdown">
      </div>

      <div class="message-time">
        <!-- (修改) 将所有按钮包裹在 .message-actions 中 -->
        <div class="message-actions">
          <!-- (新增) 点赞/点踩按钮 -->
          <button
            v-if="!isUser && content"
            class="copy-btn feedback-btn"
            :class="{ 'liked': feedbackState === 'liked' }"
            title="点赞"
            @click="handleLike"
            :disabled="feedbackState"
          >
            <thumb-up-icon class="icon-small" />
          </button>
          <button
            v-if="!isUser && content"
            class="copy-btn feedback-btn"
            :class="{ 'disliked': feedbackState === 'disliked' }"
            title="点踩"
            @click="handleDislike"
            :disabled="feedbackState"
          >
            <thumb-down-icon class="icon-small" />
          </button>
          <!-- (结束 新增) -->

          <button
            v-if="!isUser && content"
            class="copy-btn"
            :title="copied ? '已复制' : '复制内容'"
            @click="copyContent"
            :disabled="copied"
          >
            <check-icon v-if="copied" class="icon-small success" />
            <copy-icon v-else class="icon-small" />
          </button>

          <button
            v-if="allowRegenerate"
            class="copy-btn regenerate-btn" 
            title="重新生成"
            @click="$emit('regenerate')"
          >
            <refresh-icon class="icon-small" />
          </button>
        </div>
        <!-- (修改) 将时间戳单独放在 span 中，以便 flex 布局 -->
        <span class="timestamp-text">{{ formatTime(timestamp) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineProps, ref, watch, onUnmounted, defineEmits } from 'vue';
import { marked } from 'marked';
// (修改) 导入新图标
import { 
  BrainIcon, ChevronDownIcon, ChevronUpIcon, 
  CopyIcon, CheckIcon, RefreshIcon, 
  ThumbUpIcon, ThumbDownIcon 
} from 'vue-tabler-icons';

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
  thinkProcess: {
    type: String,
    default: null
  },
  duration: {
    type: Number,
    default: null
  },
  allowRegenerate: {
    type: Boolean,
    default: false
  }
});

const emits = defineEmits(['regenerate']);

const showthinkProcess = ref(false);

// (新增) 反馈状态
const feedbackState = ref(null); // null, 'liked', 'disliked'
const showLikeToast = ref(false);
const showDislikeModal = ref(false);

// (新增) 点赞处理
const handleLike = () => {
  if (feedbackState.value) return;
  feedbackState.value = 'liked';
  showLikeToast.value = true;
  setTimeout(() => {
    showLikeToast.value = false;
  }, 2000); // 2秒后隐藏提示
};

// (新增) 点踩处理
const handleDislike = () => {
  if (feedbackState.value) return;
  feedbackState.value = 'disliked';
  showDislikeModal.value = true;
};

// (新增) 关闭点踩弹窗
const closeDislikeModal = () => {
  showDislikeModal.value = false;
};

// (新增) 处理点踩后的重新生成
const handleDislikeRegenerate = () => {
  emits('regenerate');
  showDislikeModal.value = false;
};


// ... (计时器逻辑不变) ...
const displayTime = ref(props.duration ? props.duration.toFixed(1) : '0.0');
const timerId = ref(null);
watch(() => props.thinkProcess, (newThinkProcess, oldThinkProcess) => {
  if (!props.isUser && newThinkProcess && !oldThinkProcess && !props.duration && !timerId.value) {
    const startTime = Date.now();
    displayTime.value = '0.0'; 
    timerId.value = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 1000;
      displayTime.value = elapsed.toFixed(1);
    }, 100); 
  }
});
watch(() => props.duration, (newDuration) => {
  if (newDuration) {
    if (timerId.value) {
      clearInterval(timerId.value); 
      timerId.value = null;
    }
    displayTime.value = newDuration.toFixed(1);
  }
});
onUnmounted(() => {
  if (timerId.value) {
    clearInterval(timerId.value);
  }
});
// (*** 计时器逻辑结束 ***)


const copied = ref(false);
const copyContent = async () => {
  if (!props.content || copied.value) return;
  try {
    await navigator.clipboard.writeText(props.content);
    copied.value = true;
    setTimeout(() => {
      copied.value = false;
    }, 2000); 
  } catch (err) {
    console.error('Failed to copy text: ', err);
    // (修改) 避免使用 alert
    // alert('复制失败，请重试');
  }
};


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

const renderedthinkProcess = computed(() => {
  if (!props.thinkProcess) {
    return '';
  }
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
/* (修改) .message 增加 position: relative */
.message {
  position: relative; 
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

.message-content {
  padding: 0; 
  border-radius: var(--radius);
  position: relative; /* (修改) 设为 relative 以便定位弹窗 */
  width: 100%; 
}

.message:not(.user-message) .message-content {
  background-color: var(--bot-message);
}

.user-message .message-content {
  background-color: var(--user-message);
  padding: 0.75rem 1rem; 
}

.message-text {
  padding: 0.75rem 1rem;
  margin-bottom: 0.25rem;
  line-height: 1.5;
}

.user-message .message-text {
  padding: 0; 
  white-space: pre-wrap;
}

/* (修改) .message-time 布局 */
.message-time {
  font-size: 0.75rem;
  color: var(--text-secondary);
  /* (移除) text-align: right; */
  padding: 0 1rem 0.5rem; 
  display: flex;
  justify-content: space-between; /* (修改) 改为 space-between */
  align-items: center;
  /* (移除) gap: 0.5rem; */
}

.user-message .message-time {
  padding: 0; 
  display: block; 
  text-align: right; /* (恢复) 用户消息时间戳在右侧 */
}

/* (新增) 包裹按钮的 flex 容器 */
.message-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}


/* ... (已有 .think-container 样式) ... */
.think-container {
  background-color: rgba(0, 0, 0, 0.03); 
  border-bottom: 1px solid var(--border-color);
  border-top-left-radius: var(--radius);
  border-top-right-radius: var(--radius);
}

.think-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem; 
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
  flex-shrink: 0; 
}

.chevron {
  transition: transform 0.2s ease;
}

.think-content {
  padding: 0.75rem 1rem; 
  background-color: rgba(255, 255, 255, 0.5); 
}

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

/* (修改) 复制按钮样式 - 调整定位 */
.copy-btn {
  position: static; /* (修改) 改为 static，使用 flex 布局 */
  /* (移除) left, bottom */
  background: none;
  border: none;
  padding: 0.25rem;
  border-radius: var(--radius);
  cursor: pointer;
  color: var(--text-secondary);
  opacity: 0.6; /* (修改) 默认可见 */
  transition: all 0.2s ease;
  
  /* (新增) 下面的 :hover, :disabled 样式 */
}

/* (新增) 反馈按钮特定样式 */
.feedback-btn {
  /* (移除) left 定位 */
}

/* (新增) 重新生成按钮特定样式 */
.regenerate-btn {
  /* (移除) left 定位 */
}


/* (修改) 悬停效果 */
.message-content:hover .copy-btn {
    opacity: 1; /* (修改) 悬停时完全可见 */
}

.copy-btn:hover:not(:disabled) {
  background-color: rgba(0, 0, 0, 0.1);
  opacity: 1;
}

.copy-btn:disabled {
  cursor: default;
  opacity: 1; 
}

/* (新增) 反馈按钮激活状态 */
.feedback-btn.liked {
  color: var(--primary-color);
  opacity: 1;
}
.feedback-btn.disliked {
  color: var(--danger-color);
  opacity: 1;
}
.feedback-btn:disabled:not(.liked):not(.disliked) {
  /* 复制按钮的 :disabled 样式 */
  cursor: default;
  opacity: 1;
}
.feedback-btn:disabled {
  cursor: not-allowed; /* (修改) 禁用时不允许点击 */
}


.icon-small {
  width: 1rem; 
  height: 1rem;
  display: block; 
}

.icon-small.success {
  color: var(--secondary-color); 
}

/* (新增) 点赞提示 (Toast) */
.feedback-toast {
  position: absolute;
  bottom: 2.5rem; /* (修改) 放在 message-time 上方 */
  left: 1rem; /* (修改) 移到左侧 */
  background-color: var(--secondary-color);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius);
  font-size: 0.875rem;
  z-index: 10;
  animation: fade-in-out 2s ease;
}

@keyframes fade-in-out {
  0% { opacity: 0; transform: translateY(10px); }
  20% { opacity: 1; transform: translateY(0); }
  80% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(10px); }
}

/* (修改) 点踩弹窗 (Modal) - 调整定位 */
.feedback-modal-overlay {
  position: absolute;
  /* (修改) 调整 bottom 和 left 定位 */
  bottom: -10rem; /* 放在 message-time (操作栏) 的上方 */
  left: 0rem;     /* 与左侧内容对齐 */
  transform: none;  /* (修改) 移除 transform */
  z-index: 20;
  display: block;
  background-color: transparent;
  backdrop-filter: none;
  padding: 0;
  border-radius: 0;
}

.feedback-modal {
  background-color: var(--card-bg);
  padding: 1rem;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border: 1px solid var(--border-color);
  width: 300px; /* (修改) 固定宽度 */
}

.feedback-modal p {
  font-size: 0.875rem;
  color: var(--text-primary);
  margin-bottom: 1rem;
  line-height: 1.5;
}

.feedback-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

/* (新增) 用于弹窗内按钮中的小图标 */
.icon-small-inline {
  width: 1rem;
  height: 1rem;
  display: inline-block;
  vertical-align: text-bottom;
  margin-right: 0.25rem;
}
</style>

