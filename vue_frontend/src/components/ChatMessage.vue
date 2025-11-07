<template>
  <div class="message" :class="{ 'user-message': isUser }">
    <div class="message-avatar">
      <div :class="isUser ? 'user-avatar' : 'bot-avatar'">
        <user-icon v-if="isUser" class="icon-avatar" />
        <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="icon-avatar bot-logo">
          <title>DeepSeek</title>
          <path d="M23.748 4.482c-.254-.124-.364.113-.512.234-.051.039-.094.09-.137.136-.372.397-.806.657-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-.156-.708-.311-.955-.65-.172-.241-.219-.51-.305-.774-.055-.16-.11-.323-.293-.35-.2-.031-.278.136-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.393.137.093.172.187.129.323-.082.28-.18.552-.266.833-.055.179-.137.217-.329.14a5.526 5.526 0 01-1.736-1.18c-.857-.828-1.631-1.742-2.597-2.458a11.365 11.365 0 00-.689-.471c-.985-.957.13-1.743.388-1.836.27-.098.093-.432-.779-.428-.872.004-1.67.295-2.687.684a3.055 3.055 0 01-.465.137 9.597 9.597 0 00-2.883-.102c-1.885.21-3.39 1.102-4.497 2.623C.082 8.606-.231 10.684.152 12.85c.403 2.284 1.569 4.175 3.36 5.653 1.858 1.533 3.997 2.284 6.438 2.14 1.482-.085 3.133-.284 4.994-1.86.47.234.962.327 1.78.397.63.059 1.236-.03 1.705-.128.735-.156.684-.837.419-.961-2.155-1.004-1.682-.595-2.113-.926 1.096-1.296 2.746-2.642 3.392-7.003.05-.347.007-.565 0-.845-.004-.17.035-.237.23-.256a4.173 4.173 0 001.545-.475c1.396-.763 1.96-2.015 2.093-3.517.02-.23-.004-.467-.247-.588zM11.581 18c-2.089-1.642-3.102-2.183-3.52-2.16-.392.024-.321.471-.235.763.09.288.207.486.371.739.114.167.192.416-.113.603-.673.416-1.842-.14-1.897-.167-1.361-.802-2.5-1.86-3.301-3.307-.774-1.393-1.224-2.887-1.298-4.482-.02-.386.093-.522.477-.592a4.696 4.696 0 011.529-.039c2.132.312 3.946 1.265 5.468 2.774.868.86 1.525 1.887 2.202 2.891.72 1.066 1.494 2.082 2.48 2.914.348.292.625.514.891.677-.802.09-2.14.11-3.054-.614zm1-6.44a.306.306 0 01.415-.287.302.302 0 01.2.288.306.306 0 01-.31.307.303.303 0 01-.304-.308zm3.11 1.596c-.2.081-.399.151-.59.16a1.245 1.245 0 01-.798-.254c-.274-.23-.47-.358-.552-.758a1.73 1.73 0 01.016-.588c.07-.327-.008-.537-.239-.727-.187-.156-.426-.199-.688-.199a.559.559 0 01-.254-.078c-.11-.054-.2-.19-.114-.358.028-.054.16-.186.192-.21.356-.202.767-.136 1.146.016.352.144.618.408 1.001.782.391.451.462.576.685.914.176.265.336.537.445.848.067.195-.019.354-.25.452z" fill="#4D6BFE"></path>
        </svg>
      </div>
    </div>
    
    <!-- (调整) 消息内容和操作的包装器 -->
    <div class="message-wrapper">
      <!-- 新增：用户消息附件名小框（在气泡上方，独立显示） -->
      <div v-if="isUser && attachmentName" class="attachment-chip-top">
        <span class="name-text">{{ attachmentName }}</span>
      </div>

      <!-- (调整) 消息内容气泡 -->
      <div class="message-content" :class="{ 'user-content': isUser }">
        
        <!-- (调整) 思考过程 -->
        <div 
          v-if="!isUser && thinkProcess" 
          class="think-container"
        >
          <div 
            class="think-header" 
            @click="showthinkProcess = !showthinkProcess"
            :title="showthinkProcess ? '收起' : '查看思考过程'"
          >
            <div class="think-title">
              <brain-icon class="icon-small" />
              <span>思考过程</span>
            </div>
            <div class="think-meta">
              <span>耗时: {{ displayTime }}s</span>
              <chevron-down 
                class="icon-small chevron"
                :class="{ 'expanded': showthinkProcess }"
              />
            </div>
          </div>
          <!-- (新增) 折叠动画 -->
          <div v-if="showthinkProcess" class="think-content-wrapper">
            <div 
              ref="thinkContentRef"
              class="think-content" 
              v-html="renderedthinkProcess"
            >
            </div>
          </div>
        </div>

        <!-- (调整) 用户消息内容 -->
        <div v-if="isUser" ref="userTextRef" class="message-text user-message-text">
          {{ content }}
        </div>
        <!-- (调整) AI 消息内容 -->
        <div v-else ref="messageTextRef" class="message-text" v-html="renderedMarkdown">
        </div>
      </div>

      <!-- (调整) 消息操作和时间戳 -->
      <div class="message-footer">
        <div class="message-actions">
          <!-- 用户消息：编辑按钮 -->

          <button
            v-if="isUser && content && !loading"
            class="icon-button"
            :title="copied ? '已复制' : '复制内容'"
            @click="copyContent"
            :disabled="copied"
          >
            <check-icon v-if="copied" class="icon-small success" />
            <copy-icon v-else class="icon-small" />
          </button>

          <button
            v-if="isUser && content && !loading"
            class="icon-button"
            title="编辑并重新提问"
            @click="handleEdit"
          >
            <pencil-icon class="icon-small" />
          </button>
          
          <!-- AI 消息：反馈和复制按钮 -->
          <template v-if="!isUser && content && !loading">
            <button
              class="icon-button"
              :class="{ 'liked': feedbackState === 'liked' }"
              title="点赞"
              @click="handleLike"
              :disabled="!!feedbackState"
            >
              <thumb-up-icon class="icon-small" />
            </button>
            <button
              class="icon-button"
              :class="{ 'disliked': feedbackState === 'disliked' }"
              title="点踩"
              @click="handleDislike"
              :disabled="!!feedbackState"
            >
              <thumb-down-icon class="icon-small" />
            </button>
            <button
              class="icon-button"
              :title="copied ? '已复制' : '复制内容'"
              @click="copyContent"
              :disabled="copied"
            >
              <check-icon v-if="copied" class="icon-small success" />
              <copy-icon v-else class="icon-small" />
            </button>
          </template>
          
          <!-- AI 消息：重新生成按钮 -->
          <button
            v-if="allowRegenerate"
            class="icon-button" 
            title="重新生成"
            @click="$emit('regenerate')"
          >
            <refresh-icon class="icon-small" />
          </button>
        </div>
        
        <!-- (调整) 反馈弹窗 -->
        <div v-if="showLikeToast" class="feedback-toast like">
          感谢您的支持！
        </div>

        <div v-if="showDislikeModal" class="feedback-modal-overlay">
          <div class="feedback-modal card">
            <p>感谢您的反馈。是否需要重新生成回答？</p>
            <div class="feedback-modal-actions">
              <button class="secondary" @click="closeDislikeModal">取消</button>
              <button class="primary" @click="handleDislikeRegenerate">
                <refresh-icon class="icon-small-inline" />
                重新生成
              </button>
            </div>
          </div>
        </div>

        <span v-if="isUser" class="timestamp-text">{{ formatTime(timestamp) }}</span>
      </div>

      <!-- (调整) HTML/JS 模态框样式 -->
      <div v-if="showHtmlPreview" class="preview-modal-overlay" @click.self="showHtmlPreview = false">
        <div class="preview-modal card">
          <div class="preview-header">
            <h3>HTML 预览</h3>
            <button class="icon-button" @click="showHtmlPreview = false" title="关闭">
              <x-icon class="icon-small" />
            </button>
          </div>
          <div class="preview-content">
            <iframe 
              :srcdoc="htmlPreviewContent" 
              frameborder="0"
              sandbox="allow-scripts allow-same-origin allow-forms"
              class="preview-iframe"
            ></iframe>
          </div>
        </div>
      </div>

      <div v-if="showJsResult" class="preview-modal-overlay" @click.self="showJsResult = false">
        <div class="preview-modal card">
          <div class="preview-header">
            <h3>JavaScript 运行结果</h3>
            <button class="icon-button" @click="showJsResult = false" title="关闭">
              <x-icon class="icon-small" />
            </button>
          </div>
          <div class="preview-content js-result-content">
            <pre class="js-result-pre">{{ jsResultContent }}</pre>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed, defineProps, ref, watch, onUnmounted, defineEmits, onMounted, nextTick } from 'vue';
import { useStore } from '../store';
import { marked } from 'marked';
import { 
  BrainIcon, ChevronDownIcon, ChevronUpIcon, 
  CopyIcon, CheckIcon, RefreshIcon, 
  ThumbUpIcon, ThumbDownIcon,
  PlayerPlayIcon, PencilIcon, UserIcon, XIcon
} from 'vue-tabler-icons';

// ... (props 和 emits 定义保持不变) ...
const props = defineProps({
  isUser: { type: Boolean, required: true },
  content: { type: String, required: true },
  attachmentName: { type: String, default: '' },
  timestamp: { type: Date, required: true },
  thinkProcess: { type: String, default: null },
  duration: { type: Number, default: null },
  allowRegenerate: { type: Boolean, default: false },
  messageId: { type: [String, Number], default: null }
});

const emits = defineEmits(['regenerate', 'edit']);

const store = useStore();
const glossaryEntries = computed(() => store.glossary || {});

const showthinkProcess = ref(false);

const feedbackState = ref(null); 
const showLikeToast = ref(false);
const showDislikeModal = ref(false);

const handleLike = () => {
  if (feedbackState.value) return;
  feedbackState.value = 'liked';
  showLikeToast.value = true;
  setTimeout(() => { showLikeToast.value = false; }, 2000);
};

const handleDislike = () => {
  if (feedbackState.value) return;
  feedbackState.value = 'disliked';
  showDislikeModal.value = true;
};

const closeDislikeModal = () => {
  showDislikeModal.value = false;
};

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
    setTimeout(() => { copied.value = false; }, 2000); 
  } catch (err) {
    console.error('Failed to copy text: ', err);
  }
};

// (移除) 用户消息复制，合并到 handleEdit
const handleEdit = () => {
  if (!props.content || !props.messageId) return;
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
  return new Date(date).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
};

// ... (代码块复制、HTML/JS 预览功能) ...
const messageTextRef = ref(null);
const thinkContentRef = ref(null);
const codeBlockCopiedStates = ref(new Map());
const userTextRef = ref(null);

const showHtmlPreview = ref(false);
const htmlPreviewContent = ref('');
const showJsResult = ref(false);
const jsResultContent = ref('');

const addCodeBlockCopyButtons = (container) => {
  if (!container) return;
  
  const codeBlocks = container.querySelectorAll('pre');
  
  codeBlocks.forEach((pre, index) => {
    if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrapper')) return;
    
    const codeElement = pre.querySelector('code');
    const codeText = codeElement ? codeElement.innerText || codeElement.textContent : pre.innerText || pre.textContent;
    
    let isHtml = false;
    let isJavascript = false;
    if (codeElement) {
      const codeClasses = codeElement.className || '';
      isHtml = codeClasses.includes('language-html') || codeClasses.includes('lang-html');
      isJavascript = codeClasses.includes('language-javascript') ||
                     codeClasses.includes('lang-javascript') ||
                     codeClasses.includes('language-js') ||
                     codeClasses.includes('lang-js');
    }
    
    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';
    
    const parent = pre.parentNode;
    parent.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
    
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'code-block-buttons';
    
    // (调整) 复制按钮样式
    const copyBtn = document.createElement('button');
    copyBtn.className = 'code-block-btn code-copy-btn';
    copyBtn.title = '复制代码';
    copyBtn.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      <span>复制</span>
    `;
    
    const checkIcon = document.createElement('span');
    checkIcon.className = 'code-block-btn code-check-icon';
    checkIcon.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span>已复制</span>
    `;
    checkIcon.style.display = 'none';
    
    buttonContainer.appendChild(copyBtn);
    buttonContainer.appendChild(checkIcon);
    
    if (isHtml) {
      const runBtn = document.createElement('button');
      runBtn.className = 'code-block-btn code-run-btn';
      runBtn.title = '运行 HTML';
      runBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <span>运行</span>
      `;
      runBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        htmlPreviewContent.value = codeText;
        showHtmlPreview.value = true;
      });
      buttonContainer.appendChild(runBtn);
    }
    
    if (isJavascript) {
      const runBtn = document.createElement('button');
      runBtn.className = 'code-block-btn code-run-btn';
      runBtn.title = '运行 JavaScript';
      runBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <span>运行</span>
      `;
      runBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        executeJavaScript(codeText);
      });
      buttonContainer.appendChild(runBtn);
    }
    
    wrapper.appendChild(buttonContainer);
    
    copyBtn.addEventListener('click', async (e) => {
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(codeText);
        copyBtn.style.display = 'none';
        checkIcon.style.display = 'flex';
        codeBlockCopiedStates.value.set(index, true);
        setTimeout(() => {
          copyBtn.style.display = 'flex';
          checkIcon.style.display = 'none';
          codeBlockCopiedStates.value.set(index, false);
        }, 2000);
      } catch (err) {
        console.error('Failed to copy code: ', err);
      }
    });
  });
};

const SKIP_TAGS = new Set(['CODE', 'PRE', 'SCRIPT', 'STYLE']);

const applyGlossaryTooltips = (container) => {
  if (!container) return;
  const entries = glossaryEntries.value;
  const terms = Object.keys(entries || {});
  if (terms.length === 0) return;

  const sortedTerms = terms
    .map((term) => ({
      term,
      lower: term.toLowerCase(),
      explanation: entries[term],
    }))
    .sort((a, b) => b.term.length - a.term.length);

  const walker = document.createTreeWalker(
    container,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode(node) {
        if (!node.parentElement) return NodeFilter.FILTER_REJECT;
        if (SKIP_TAGS.has(node.parentElement.tagName)) return NodeFilter.FILTER_REJECT;
        if (node.parentElement.closest('.glossary-term')) return NodeFilter.FILTER_REJECT;
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    },
    false
  );

  const textNodes = [];
  while (walker.nextNode()) {
    textNodes.push(walker.currentNode);
  }

  textNodes.forEach((node) => {
    const originalText = node.nodeValue;
    const lowerText = originalText.toLowerCase();
    let currentIndex = 0;
    const fragments = [];

    while (currentIndex < originalText.length) {
      let matchedEntry = null;
      let matchedIndex = -1;

      for (const entry of sortedTerms) {
        const idx = lowerText.indexOf(entry.lower, currentIndex);
        if (idx !== -1 && (matchedIndex === -1 || idx < matchedIndex)) {
          matchedIndex = idx;
          matchedEntry = entry;
        }
      }

      if (!matchedEntry) {
        break;
      }

      if (matchedIndex > currentIndex) {
        fragments.push(document.createTextNode(originalText.slice(currentIndex, matchedIndex)));
      }

      const matchedText = originalText.slice(
        matchedIndex,
        matchedIndex + matchedEntry.term.length
      );

      const span = document.createElement('span');
      span.className = 'glossary-term';
      span.setAttribute('tabindex', '0');
      span.dataset.term = matchedEntry.term;
      span.textContent = matchedText;

      const tooltip = document.createElement('span');
      tooltip.className = 'glossary-tooltip';
      tooltip.textContent = matchedEntry.explanation || matchedEntry.term;

      span.appendChild(tooltip);
      fragments.push(span);

      currentIndex = matchedIndex + matchedText.length;
    }

    if (fragments.length > 0) {
      if (currentIndex < originalText.length) {
        fragments.push(document.createTextNode(originalText.slice(currentIndex)));
      }

      const parent = node.parentNode;
      fragments.forEach((fragment) => {
        parent.insertBefore(fragment, node);
      });
      parent.removeChild(node);
    }
  });
};

const enhanceAssistantContent = () => {
  nextTick(() => {
    if (!messageTextRef.value) return;
    addCodeBlockCopyButtons(messageTextRef.value);
    applyGlossaryTooltips(messageTextRef.value);
  });
};

const enhanceThinkContent = () => {
  nextTick(() => {
    if (!thinkContentRef.value) return;
    addCodeBlockCopyButtons(thinkContentRef.value);
    applyGlossaryTooltips(thinkContentRef.value);
  });
};

const enhanceUserContent = () => {
  nextTick(() => {
    if (!userTextRef.value) return;
    applyGlossaryTooltips(userTextRef.value);
  });
};

watch(() => renderedMarkdown.value, () => {
  if (!props.isUser) {
    enhanceAssistantContent();
  }
}, { immediate: true });

watch(() => [renderedthinkProcess.value, showthinkProcess.value], () => {
  if (!props.isUser && showthinkProcess.value) {
    enhanceThinkContent();
  }
}, { immediate: true });

watch(() => props.content, () => {
  if (props.isUser) {
    enhanceUserContent();
  }
}, { immediate: true });

watch(glossaryEntries, () => {
  if (props.isUser) {
    enhanceUserContent();
  } else {
    enhanceAssistantContent();
    if (showthinkProcess.value) {
      enhanceThinkContent();
    }
  }
}, { immediate: true });

// ... (executeJavaScript 保持不变) ...
const executeJavaScript = (code) => {
  const logs = [];
  let returnValue = undefined;
  let error = null;
  const oldLog = console.log;
  const oldError = console.error;
  const oldWarn = console.warn;
  const oldInfo = console.info;
  
  try {
    const logHelper = (type) => (...args) => {
      logs.push(`[${type}] ${args.map(arg => {
        try {
          return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
        } catch (e) { return String(arg); }
      }).join(' ')}`);
    };
    console.log = logHelper('LOG');
    console.error = logHelper('ERROR');
    console.warn = logHelper('WARN');
    console.info = logHelper('INFO');
    
    const func = new Function(code);
    returnValue = func();
  } catch (e) {
    error = e;
  } finally {
    console.log = oldLog;
    console.error = oldError;
    console.warn = oldWarn;
    console.info = oldInfo;
  }
  
  let resultText = '';
  if (logs.length > 0) {
    resultText += '=== Console 输出 ===\n' + logs.join('\n') + '\n\n';
  }
  if (returnValue !== undefined) {
    resultText += '=== 返回值 ===\n';
    try {
      resultText += typeof returnValue === 'object' ? JSON.stringify(returnValue, null, 2) : String(returnValue);
    } catch(e) { resultText += String(returnValue); }
    resultText += '\n\n';
  }
  if (error) {
    resultText += '=== 错误信息 ===\n' + error.toString() + (error.stack ? '\n\n' + error.stack : '');
  }
  if (!resultText.trim()) {
    resultText = '代码执行完成，无输出。';
  }
  
  jsResultContent.value = resultText;
  showJsResult.value = true;
};


onMounted(() => {
  if (props.isUser) {
    enhanceUserContent();
  } else {
    enhanceAssistantContent();
    if (showthinkProcess.value) {
      enhanceThinkContent();
    }
  }
});
</script>

<style scoped>
/* (调整) 基础布局 */
.message {
  display: flex;
  gap: 1rem; /* 头像和内容的间距 */
  /* (修改) 默认 max-width 应用于 AI 消息 */
  max-width: 70%; 
  overflow: visible;
}

.message.user-message {
  margin-left: auto;
  flex-direction: row-reverse;
  max-width: 60%; /* 示例：将用户消息宽度调整为 50% */
}

.message.user-message {
  margin-left: auto;
  flex-direction: row-reverse;
}

/* (调整) 头像样式 */
.message-avatar {
  flex-shrink: 0;
  margin-top: 0.25rem; /* (新增) 微调对齐 */
}

.user-avatar, .bot-avatar {
  width: 2.25rem; /* (调整) 尺寸 */
  height: 2.25rem;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
}

.user-avatar {
  background-color: var(--primary-light);
  color: var(--primary-dark);
}

.bot-avatar {
  background-color: var(--bg-color);
  border: 1px solid var(--border-color);
  color: var(--primary-color);
}

.icon-avatar {
  width: 1.25rem;
  height: 1.25rem;
}
.bot-logo {
  stroke-width: 2.5;
}

/* (新增) 消息包装器 */
.message-wrapper {
  display: flex;
  flex-direction: column;
  min-width: 100px;
  overflow: visible; /* 确保弹窗可见 */
  width: 100%;
}

/* (调整) 消息气泡 */
.message-content {
  padding: 0; 
  border-radius: var(--radius);
  position: relative;
  border: 1px solid var(--border-color);
  background-color: var(--card-bg);
  box-shadow: var(--shadow-sm);
  overflow: visible;
}

/* 新增：用户消息附件名顶部小框（独立于气泡） */
.attachment-chip-top {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  align-self: flex-end; /* 与用户消息对齐到右侧 */
  background-color: var(--bg-color);
  border: 1px dashed var(--border-color);
  color: var(--text-secondary);
  border-radius: var(--radius);
  padding: 0.25rem 0.5rem;
  margin-bottom: 0.375rem; /* 与气泡保持间距 */
  font-size: 0.85rem;
}
.attachment-chip-top .paperclip {
  line-height: 1;
}
.attachment-chip-top .name-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 18rem;
}

.message-content.user-content {
  background-color: #f0f4f9;
  border: none;
  box-shadow: none;
}

/* (调整) 消息文本 */
.message-text {
  padding: 1rem 1.5rem;
  line-height: 1.6;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.user-message-text {
  white-space: pre-wrap;
  color: var(--user-message-text);
}

/* (调整) 思考过程 */
.think-container {
  background-color: transparent; 
  border-bottom: 1px solid var(--border-color);
}
.user-content .think-container {
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.think-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.625rem 1rem; 
  cursor: pointer;
  user-select: none;
  background-color: var(--bg-color);
}
.think-header:hover {
  background-color: var(--border-color);
}

.think-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-secondary);
}
.think-title .icon-small {
  color: var(--text-secondary);
}

.think-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-light);
}

.chevron {
  transition: transform 0.2s ease;
}
.chevron.expanded {
  transform: rotate(180deg);
}

.think-content-wrapper {
  /* (新增) 折叠动画 (需要 JS 配合) */
  overflow: hidden;
}
.think-content {
  padding: 1rem 1.5rem;
  background-color: var(--card-bg); 
  font-size: 0.9rem;
}
:deep(.think-content p:last-child) {
  margin-bottom: 0;
}

/* (调整) 消息底部 (操作 + 时间) */
.message-footer {
  position: relative; /* (新增) 相对定位，用于弹窗 */
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.5rem;
  gap: 0.5rem;
}

/* 调整用户消息下的操作容器，使其靠右 */
.user-message .message-actions {
  /* 确保操作按钮不会被时间戳挤压 */
  order: 1; /* 确保在 flex 容器中位于最右侧 */
}

.message-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

/* (新增) 图标按钮通用样式 */
.icon-button {
  background: none;
  border: none;
  padding: 0.375rem;
  border-radius: var(--radius);
  color: var(--text-light);
  cursor: pointer;
  transition: all 0.2s ease;
}

.icon-button:hover:not(:disabled) {
  background-color: var(--bg-color);
  color: var(--text-primary);
}

.icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.8;
}

/* (调整) 时间戳 */
.timestamp-text {
  font-size: 0.75rem;
  color: var(--text-light);
  flex-shrink: 0;
}
.user-message .timestamp-text {
  color: var(--text-light);
}

/* (调整) 反馈按钮状态 */
.icon-button.liked {
  color: var(--primary-color);
}
.icon-button.disliked {
  color: var(--danger-color);
}
.icon-small.success {
  color: var(--secondary-color); 
}

/* (调整) 反馈弹窗和提示 */
.feedback-toast {
  position: absolute;
  bottom: -3rem; /* (调整) 相对 .message-footer 定位 */
  left: 0;
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

.feedback-modal-overlay {
  position: absolute;
  bottom: -7rem; /* (调整) 相对 .message-footer 定位 */
  left: 3rem;
  z-index: 20;
}

.feedback-modal {
  height: 100px;
  width: 350px;
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
  gap: 1rem;
}
.icon-small-inline {
  width: 1rem;
  height: 1rem;
  display: inline-block;
  vertical-align: text-bottom;
  margin-right: 0.25rem;
}


/* (调整) 代码块样式 */
:deep(.code-block-wrapper) {
  position: relative;
  margin: 0.75rem 0;
}

:deep(.code-block-buttons) {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  display: flex;
  gap: 0.5rem;
  z-index: 5;
}

:deep(.code-block-btn) {
  background-color: rgba(255, 255, 255, 0.8);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  backdrop-filter: blur(2px);
  opacity: 0.8;
}
:deep(.code-block-btn:hover) {
  opacity: 1;
  background-color: white;
  border-color: #ccc;
}
:deep(.code-block-btn svg) {
  width: 0.875rem;
  height: 0.875rem;
}

:deep(.code-check-icon) {
  color: var(--secondary-color);
  border-color: var(--secondary-color);
}
:deep(.code-run-btn) {
  color: var(--primary-color);
}

:deep(pre) {
  position: relative;
  margin: 0;
  padding-top: 2.5rem; /* (新增) 为按钮留出空间 */
}

/* (调整) 预览模态框 */
.preview-modal-overlay {
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
  from { opacity: 0; }
  to { opacity: 1; }
}

.preview-modal {
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
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0.75rem 0.75rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.preview-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

.preview-content {
  flex: 1;
  overflow: auto;
  position: relative;
  background-color: var(--bg-color);
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  background-color: white;
}

.js-result-content {
  padding: 1rem 1.5rem;
  background-color: #1e1e1e; /* (固定) 深色背景 */
}
.js-result-pre {
  margin: 0;
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

:deep(.glossary-term) {
  position: relative;
  cursor: help;
  border-bottom: 1px dashed var(--primary-color);
  color: inherit;
  transition: color 0.2s ease;
}

:deep(.glossary-term:focus-visible) {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

:deep(.glossary-term .glossary-tooltip) {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: calc(100% + 0.5rem);
  background-color: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 0.5rem 0.75rem;
  color: var(--text-primary);
  font-size: 0.75rem;
  line-height: 1.4;
  width: max-content;
  max-width: 360px;
  min-width: 160px;
  white-space: normal;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease, transform 0.15s ease;
  z-index: 25;
}

:deep(.glossary-term:hover .glossary-tooltip),
:deep(.glossary-term:focus .glossary-tooltip) {
  opacity: 1;
  transform: translate(-50%, -0.25rem);
  pointer-events: auto;
}
</style>
