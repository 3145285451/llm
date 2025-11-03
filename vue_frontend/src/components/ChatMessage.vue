<template>
  <div class="message" :class="{ 'user-message': isUser }">
    <div class="message-avatar">
      <div :class="isUser ? 'user-avatar' : 'bot-avatar'">
        {{ isUser ? '用户' : 'AI' }}
      </div>
    </div>
    <div class="message-content">
      
      <div v-if="showLikeToast" class="feedback-toast like">
        感谢您的支持！
      </div>

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
          ref="thinkContentRef"
          class="think-content" 
          v-html="renderedthinkProcess"
        >
        </div>
      </div>

      <div v-if="isUser" class="message-text user-message-text-wrapper">
        <div v-if="content" class="user-action-buttons">
          <!-- 复制按钮 -->
          <button
            class="user-copy-btn"
            :title="userCopied ? '已复制' : '复制我的提问'"
            @click="copyUserContent"
            :disabled="userCopied"
          >
            <check-icon v-if="userCopied" class="icon-small success" />
            <copy-icon v-else class="icon-small" />
          </button>
          <!-- 编辑按钮 -->
          <button
            class="user-edit-btn"
            title="编辑并重新生成"
            @click="handleEdit"
          >
            <pencil-icon class="icon-small" />
          </button>
        </div>
        <div class="user-message-content">{{ content }}</div>
      </div>
      <div v-else ref="messageTextRef" class="message-text" v-html="renderedMarkdown">
      </div>

      <!-- HTML 预览模态框 -->
      <div v-if="showHtmlPreview" class="html-preview-modal-overlay" @click.self="showHtmlPreview = false">
        <div class="html-preview-modal">
          <div class="html-preview-header">
            <h3>HTML 预览</h3>
            <button class="html-preview-close-btn" @click="showHtmlPreview = false" title="关闭">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="html-preview-content">
            <iframe 
              :srcdoc="htmlPreviewContent" 
              frameborder="0"
              sandbox="allow-scripts allow-same-origin allow-forms"
              class="html-preview-iframe"
            ></iframe>
          </div>
        </div>
      </div>

      <!-- JavaScript 运行结果模态框 -->
      <div v-if="showJsResult" class="js-result-modal-overlay" @click.self="showJsResult = false">
        <div class="js-result-modal">
          <div class="js-result-header">
            <h3>JavaScript 运行结果</h3>
            <button class="js-result-close-btn" @click="showJsResult = false" title="关闭">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div class="js-result-content">
            <pre class="js-result-pre">{{ jsResultContent }}</pre>
          </div>
        </div>
      </div>

      <div class="message-time">
        <!-- 将所有按钮包裹在 .message-actions 中 -->
        <div class="message-actions">
          <!-- 点赞/点踩按钮 -->
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
        <!-- 将时间戳单独放在 span 中，以便 flex 布局 -->
        <span class="timestamp-text">{{ formatTime(timestamp) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineProps, ref, watch, onUnmounted, defineEmits, onMounted, nextTick } from 'vue';
import { marked } from 'marked';
// 导入新图标
import { 
  BrainIcon, ChevronDownIcon, ChevronUpIcon, 
  CopyIcon, CheckIcon, RefreshIcon, 
  ThumbUpIcon, ThumbDownIcon,
  PlayerPlayIcon,
  PencilIcon
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
  },
  // 消息ID
  messageId: {
    type: [String, Number],
    default: null
  }
});

const emits = defineEmits(['regenerate', 'edit']);

const showthinkProcess = ref(false);

// 反馈状态
const feedbackState = ref(null); // null, 'liked', 'disliked'
const showLikeToast = ref(false);
const showDislikeModal = ref(false);

// 点赞处理
const handleLike = () => {
  if (feedbackState.value) return;
  feedbackState.value = 'liked';
  showLikeToast.value = true;
  setTimeout(() => {
    showLikeToast.value = false;
  }, 2000); // 2秒后隐藏提示
};

// 点踩处理
const handleDislike = () => {
  if (feedbackState.value) return;
  feedbackState.value = 'disliked';
  showDislikeModal.value = true;
};

// 关闭点踩弹窗
const closeDislikeModal = () => {
  showDislikeModal.value = false;
};

// 处理点踩后的重新生成
const handleDislikeRegenerate = () => {
  emits('regenerate');
  showDislikeModal.value = false;
};

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
  }
};

// 用户消息复制状态
const userCopied = ref(false);
const copyUserContent = async () => {
  if (!props.content || userCopied.value) return;
  try {
    await navigator.clipboard.writeText(props.content);
    userCopied.value = true;
    setTimeout(() => {
      userCopied.value = false;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy user message: ', err);
  }
};

// 处理编辑按钮点击
const handleEdit = () => {
  if (!props.content || !props.messageId) return;
  // 发出编辑事件，传递消息ID和内容
  emits('edit', {
    messageId: props.messageId,
    content: props.content
  });
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

// 代码块复制功能
const messageTextRef = ref(null);
const thinkContentRef = ref(null);
const codeBlockCopiedStates = ref(new Map()); // 存储每个代码块的复制状态

// HTML 预览模态框状态
const showHtmlPreview = ref(false);
const htmlPreviewContent = ref('');

// JavaScript 运行结果模态框状态
const showJsResult = ref(false);
const jsResultContent = ref('');

// 为代码块添加复制按钮
const addCodeBlockCopyButtons = (container) => {
  if (!container) return;
  
  // 查找所有代码块
  const codeBlocks = container.querySelectorAll('pre');
  
  codeBlocks.forEach((pre, index) => {
    // 检查是否已经添加过按钮（检查父元素是否是 wrapper）
    if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrapper')) return;
    
    // 获取代码内容
    const codeElement = pre.querySelector('code');
    const codeText = codeElement ? codeElement.innerText || codeElement.textContent : pre.innerText || pre.textContent;
    
    // 检测代码块语言
    let isHtml = false;
    let isJavascript = false;
    if (codeElement) {
      const codeClasses = codeElement.className || '';
      // marked.js 通常生成 "language-html" 类名
      isHtml = codeClasses.includes('language-html') || 
               codeClasses.includes('lang-html') ||
               codeElement.classList.contains('language-html') ||
               codeElement.classList.contains('lang-html');
      
      // 检测 JavaScript 代码块
      isJavascript = codeClasses.includes('language-javascript') ||
                     codeClasses.includes('lang-javascript') ||
                     codeClasses.includes('language-js') ||
                     codeClasses.includes('lang-js') ||
                     codeElement.classList.contains('language-javascript') ||
                     codeElement.classList.contains('lang-javascript') ||
                     codeElement.classList.contains('language-js') ||
                     codeElement.classList.contains('lang-js');
    }
    
    // 创建包装器
    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';
    
    // 将 pre 元素移动到包装器中
    const parent = pre.parentNode;
    parent.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
    
    // 创建按钮容器
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'code-block-buttons';
    
    // 创建复制按钮
    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-block-copy-btn';
    copyBtn.title = '复制代码';
    copyBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
    `;
    
    // 创建成功图标（复制成功后显示）
    const checkIcon = document.createElement('span');
    checkIcon.className = 'code-block-check-icon';
    checkIcon.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
    `;
    checkIcon.style.display = 'none';
    
    buttonContainer.appendChild(copyBtn);
    buttonContainer.appendChild(checkIcon);
    
    // 如果是 HTML 代码块，添加运行按钮
    if (isHtml) {
      const runBtn = document.createElement('button');
      runBtn.className = 'code-block-run-btn';
      runBtn.title = '运行 HTML';
      runBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
      `;
      
      runBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        // 打开 HTML 预览模态框
        htmlPreviewContent.value = codeText;
        showHtmlPreview.value = true;
      });
      
      buttonContainer.appendChild(runBtn);
    }
    
    // 如果是 JavaScript 代码块，添加运行按钮
    if (isJavascript) {
      const runBtn = document.createElement('button');
      runBtn.className = 'code-block-run-btn';
      runBtn.title = '运行 JavaScript';
      runBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
      `;
      
      runBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        // 执行 JavaScript 代码并显示结果
        executeJavaScript(codeText);
      });
      
      buttonContainer.appendChild(runBtn);
    }
    
    wrapper.appendChild(buttonContainer);
    
    // 添加点击事件
    copyBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      
      try {
        await navigator.clipboard.writeText(codeText);
        
        // 显示成功状态
        copyBtn.style.display = 'none';
        checkIcon.style.display = 'block';
        
        // 存储状态
        codeBlockCopiedStates.value.set(index, true);
        
        // 2秒后恢复
        setTimeout(() => {
          copyBtn.style.display = 'block';
          checkIcon.style.display = 'none';
          codeBlockCopiedStates.value.set(index, false);
        }, 2000);
      } catch (err) {
        console.error('Failed to copy code: ', err);
      }
    });
  });
};

// 监听 Markdown 渲染变化
watch(() => renderedMarkdown.value, () => {
  if (!props.isUser) {
    nextTick(() => {
      addCodeBlockCopyButtons(messageTextRef.value);
    });
  }
}, { immediate: true });

// 监听思考过程渲染变化
watch(() => [renderedthinkProcess.value, showthinkProcess.value], () => {
  if (showthinkProcess.value && thinkContentRef.value) {
    nextTick(() => {
      addCodeBlockCopyButtons(thinkContentRef.value);
    });
  }
}, { immediate: true });

// 执行 JavaScript 代码并捕获结果
const executeJavaScript = (code) => {
  const logs = [];
  let returnValue = undefined;
  let error = null;
  
  // 保存原始的 console.log
  const oldLog = console.log;
  const oldError = console.error;
  const oldWarn = console.warn;
  const oldInfo = console.info;
  
  try {
    // 拦截 console.log 等方法
    console.log = (...args) => {
      logs.push(`[LOG] ${args.map(arg => {
        if (typeof arg === 'object') {
          try {
            return JSON.stringify(arg, null, 2);
          } catch (e) {
            return String(arg);
          }
        }
        return String(arg);
      }).join(' ')}`);
    };
    
    console.error = (...args) => {
      logs.push(`[ERROR] ${args.map(arg => {
        if (typeof arg === 'object') {
          try {
            return JSON.stringify(arg, null, 2);
          } catch (e) {
            return String(arg);
          }
        }
        return String(arg);
      }).join(' ')}`);
    };
    
    console.warn = (...args) => {
      logs.push(`[WARN] ${args.map(arg => {
        if (typeof arg === 'object') {
          try {
            return JSON.stringify(arg, null, 2);
          } catch (e) {
            return String(arg);
          }
        }
        return String(arg);
      }).join(' ')}`);
    };
    
    console.info = (...args) => {
      logs.push(`[INFO] ${args.map(arg => {
        if (typeof arg === 'object') {
          try {
            return JSON.stringify(arg, null, 2);
          } catch (e) {
            return String(arg);
          }
        }
        return String(arg);
      }).join(' ')}`);
    };
    
    // 使用 new Function() 执行代码
    const func = new Function(code);
    returnValue = func();
    
  } catch (e) {
    error = e;
  } finally {
    // 恢复原始的 console 方法
    console.log = oldLog;
    console.error = oldError;
    console.warn = oldWarn;
    console.info = oldInfo;
  }
  
  // 格式化输出结果
  let resultText = '';
  
  // 添加 console 输出
  if (logs.length > 0) {
    resultText += '=== Console 输出 ===\n';
    resultText += logs.join('\n') + '\n\n';
  }
  
  // 添加返回值
  if (returnValue !== undefined) {
    resultText += '=== 返回值 ===\n';
    if (typeof returnValue === 'object') {
      try {
        resultText += JSON.stringify(returnValue, null, 2) + '\n\n';
      } catch (e) {
        resultText += String(returnValue) + '\n\n';
      }
    } else {
      resultText += String(returnValue) + '\n\n';
    }
  }
  
  // 添加错误信息
  if (error) {
    resultText += '=== 错误信息 ===\n';
    resultText += error.toString() + '\n';
    if (error.stack) {
      resultText += '\n堆栈跟踪:\n' + error.stack;
    }
  }
  
  // 如果没有输出，显示提示
  if (!resultText.trim()) {
    resultText = '代码执行完成，无输出。';
  }
  
  // 显示结果
  jsResultContent.value = resultText;
  showJsResult.value = true;
};

// 组件挂载后也执行一次
onMounted(() => {
  if (!props.isUser) {
    nextTick(() => {
      addCodeBlockCopyButtons(messageTextRef.value);
      if (showthinkProcess.value) {
        addCodeBlockCopyButtons(thinkContentRef.value);
      }
    });
  }
});
</script>

<style scoped>
/* .message 增加 position: relative */
.message {
  position: relative; 
  display: flex;
  margin-bottom: 1rem;
  max-width: 80%;
  overflow: visible; /* 确保按钮不被裁剪 */
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
  min-width: 100px;
  padding: 0; 
  border-radius: var(--radius);
  position: relative; /* 设为 relative 以便定位弹窗 */
  width: 100%;
  overflow: visible; /* 确保按钮不被裁剪 */
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

/* 用户消息文本包装器 */
.user-message-text-wrapper {
  position: relative;
  padding: 0.75rem 1rem;
  overflow: visible; /* 确保按钮不被裁剪 */
}

.user-message-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* 用户消息操作按钮容器 - 定位到气泡左下方 */
.user-action-buttons {
  position: absolute;
  bottom: -5rem; /* 距离消息框底部 */
  left: -1rem; /* 距离消息框左侧 */
  display: flex;
  flex-direction: row; /* 按钮水平排列 */
  gap: 0.3rem; /* 按钮之间的间距 */
  z-index: 10;
}

/* 用户消息复制按钮 */
.user-copy-btn,
.user-edit-btn {
  background: none;
  border: none;
  padding: 0.25rem;
  border-radius: var(--radius);
  cursor: pointer;
  color: var(--text-secondary);
  opacity: 0.6;
  transition: all 0.2s ease;
}

.user-copy-btn:hover:not(:disabled),
.user-edit-btn:hover {
  background-color: rgba(0, 0, 0, 0.1);
  opacity: 1;
}

/* 调整 .message-time 的布局 */
.message-time {
  display: flex;
  flex-wrap: wrap; /* 允许按钮和时间戳换行 */
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem; /* 增加按钮和时间戳之间的间距 */
  padding: 0 1rem 0.5rem;
}

/* 用户消息的时间布局 */
.user-message .message-time {
  justify-content: flex-end; /* 按钮和时间戳靠右 */
  flex-wrap: nowrap; /* 禁止换行 */
  gap: 0.5rem;
  margin-top: 1rem; /* 与消息框的间距 */
  padding: 0; /* 移除内边距 */
}

/* 包裹按钮的 flex 容器 */
.message-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}


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

/* 复制按钮样式 - 调整定位 */
.copy-btn {
  position: static; /* 改为 static，使用 flex 布局 */
  /* left, bottom */
  background: none;
  border: none;
  padding: 0.25rem;
  border-radius: var(--radius);
  cursor: pointer;
  color: var(--text-secondary);
  opacity: 0.6; /* 默认可见 */
  transition: all 0.2s ease;
  
  /* 下面的 :hover, :disabled 样式 */
}


/* 悬停效果 */
.message-content:hover .copy-btn {
    opacity: 1; /* 悬停时完全可见 */
}

.copy-btn:hover:not(:disabled) {
  background-color: rgba(0, 0, 0, 0.1);
  opacity: 1;
}

.copy-btn:disabled {
  cursor: default;
  opacity: 1; 
}

/* 反馈按钮激活状态 */
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
  cursor: not-allowed; /* 禁用时不允许点击 */
}


.icon-small {
  width: 1rem; 
  height: 1rem;
  display: block; 
}

.icon-small.success {
  color: var(--secondary-color); 
}

/* 点赞提示 (Toast) */
.feedback-toast {
  position: absolute;
  bottom: 2.5rem; /* 放在 message-time 上方 */
  left: 1rem; /* 移到左侧 */
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

/* 点踩弹窗 (Modal) - 调整定位 */
.feedback-modal-overlay {
  position: absolute;
  /* 调整 bottom 和 left 定位 */
  bottom: -10rem; /* 放在 message-time (操作栏) 的上方 */
  left: 0rem;     /* 与左侧内容对齐 */
  transform: none;  /* 移除 transform */
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
  width: 300px; /* 固定宽度 */
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

/* 用于弹窗内按钮中的小图标 */
.icon-small-inline {
  width: 1rem;
  height: 1rem;
  display: inline-block;
  vertical-align: text-bottom;
  margin-right: 0.25rem;
}

/* 代码块包装器样式 */
:deep(.code-block-wrapper) {
  position: relative;
  margin: 0.5rem 0;
}

/* 代码块按钮容器样式 */
:deep(.code-block-buttons) {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: flex;
  gap: 0.25rem;
  z-index: 10;
}

/* 代码块复制按钮样式 */
:deep(.code-block-copy-btn),
:deep(.code-block-check-icon),
:deep(.code-block-run-btn) {
  background-color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  padding: 0.375rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  opacity: 0.8;
}

:deep(.code-block-copy-btn:hover),
:deep(.code-block-run-btn:hover) {
  background-color: rgba(255, 255, 255, 1);
  opacity: 1;
  border-color: rgba(0, 0, 0, 0.2);
}

:deep(.code-block-check-icon) {
  background-color: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
  color: #22c55e;
}

:deep(.code-block-run-btn) {
  background-color: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
}

:deep(.code-block-run-btn:hover) {
  background-color: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.5);
}

:deep(.code-block-copy-btn svg),
:deep(.code-block-check-icon svg),
:deep(.code-block-run-btn svg) {
  width: 1rem;
  height: 1rem;
  display: block;
}

/* 代码块容器样式调整 */
:deep(pre) {
  position: relative;
  margin: 0;
}

/* HTML 预览模态框样式 */
.html-preview-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fade-in 0.2s ease;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.html-preview-modal {
  background-color: var(--card-bg, #ffffff);
  border-radius: 8px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 90%;
  max-width: 900px;
  height: 80%;
  max-height: 700px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slide-up 0.3s ease;
}

@keyframes slide-up {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.html-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  flex-shrink: 0;
}

.html-preview-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #111827);
}

.html-preview-close-btn {
  background: none;
  border: none;
  padding: 0.25rem;
  cursor: pointer;
  color: var(--text-secondary, #6b7280);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.html-preview-close-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: var(--text-primary, #111827);
}

.html-preview-close-btn svg {
  width: 1.25rem;
  height: 1.25rem;
}

.html-preview-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.html-preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

/* JavaScript 运行结果模态框样式 */
.js-result-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fade-in 0.2s ease;
}

.js-result-modal {
  background-color: var(--card-bg, #ffffff);
  border-radius: 8px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 90%;
  max-width: 800px;
  height: 70%;
  max-height: 600px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slide-up 0.3s ease;
}

.js-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  flex-shrink: 0;
}

.js-result-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary, #111827);
}

.js-result-close-btn {
  background: none;
  border: none;
  padding: 0.25rem;
  cursor: pointer;
  color: var(--text-secondary, #6b7280);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.js-result-close-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: var(--text-primary, #111827);
}

.js-result-close-btn svg {
  width: 1.25rem;
  height: 1.25rem;
}

.js-result-content {
  flex: 1;
  overflow: auto;
  padding: 1rem 1.5rem;
  background-color: var(--code-bg, #1e1e1e);
}

.js-result-pre {
  margin: 0;
  padding: 1rem;
  background-color: var(--code-bg, #1e1e1e);
  color: var(--code-text, #d4d4d4);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
</style>

