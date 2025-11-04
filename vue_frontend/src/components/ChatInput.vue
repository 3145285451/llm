<template>
  <div class="chat-input-area">
    <!-- (调整) 搜索选项开关样式 -->
    <div class="chat-options">
      <label class="option-label" for="db-search-toggle" title="查询本地知识库">
        <input
          type="checkbox"
          id="db-search-toggle"
          class="custom-checkbox"
          v-model="useDbSearch"
        />
        <span class="checkbox-icon">
          <database-icon class="icon-small" />
        </span>
        <span>数据库查询</span>
      </label>
      <label class="option-label" for="web-search-toggle" title="使用互联网搜索">
        <input
          type="checkbox"
          id="web-search-toggle"
          class="custom-checkbox"
          v-model="useWebSearch"
        />
        <span class="checkbox-icon">
          <world-icon class="icon-small" />
        </span>
        <span>联网搜索</span>
      </label>
    </div>

    <!-- (调整) 输入框和按钮的包装器 -->
    <div class="input-wrapper" :class="{ 'focused': isFocused }">
      <textarea
        ref="textareaRef"
        v-model="message"
        class="chat-input"
        placeholder="输入您的问题或日志信息"
        @keyup.enter.exact.prevent="sendMessage"
        @keyup.enter.shift.exact="addNewline"
        @input="autoResize"
        @focus="isFocused = true"
        @blur="isFocused = false"
        :disabled="loading"
        rows="1"
      ></textarea>
      
      <!-- (调整) 发送按钮 -->
      <button 
        class="send-button" 
        @click="sendMessage"
        :disabled="!message.trim() || loading"
        title="发送消息"
      >
        <span v-if="loading" class="loading"></span>
        <send-icon v-else class="icon" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, defineExpose, nextTick, computed } from 'vue';
import { useStore } from '../store';
// (新增) 导入图标
import { SendIcon, DatabaseIcon, WorldIcon } from 'vue-tabler-icons';

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
});

const emits = defineEmits(['send']);

const message = ref('');
const textareaRef = ref(null);
const isFocused = ref(false); // (新增) 跟踪聚焦状态

const store = useStore();

const useDbSearch = computed({
  get: () => store.useDbSearch,
  set: (value) => store.setUseDbSearch(value)
});

const useWebSearch = computed({
  get: () => store.useWebSearch,
  set: (value) => store.setUseWebSearch(value)
});

// (新增) 文本域自动调整高度
const autoResize = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto';
    textareaRef.value.style.height = `${textareaRef.value.scrollHeight}px`;
  }
};

const setContent = (content) => {
  message.value = content || '';
  nextTick(autoResize);
};

const focus = () => {
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.focus();
      textareaRef.value.setSelectionRange(
        textareaRef.value.value.length, 
        textareaRef.value.value.length
      );
    }
  });
};

const sendMessage = () => {
  const content = message.value.trim();
  if (content && !props.loading) { // (新增) 检查 loading
    emits('send', content);
    message.value = '';
    nextTick(autoResize); // (新增) 发送后重置高度
  }
};

const clearInput = () => {
  message.value = '';
  nextTick(autoResize); // (新增) 清除后重置高度
};

const addNewline = (e) => {
  // (修改) 确保 addNewline 正常工作
  e.preventDefault();
  const el = textareaRef.value;
  if (!el) return;

  const start = el.selectionStart;
  const end = el.selectionEnd;
  
  // 插入换行符
  message.value = message.value.substring(0, start) + '\n' + message.value.substring(end);
  
  // 移动光标
  nextTick(() => {
    el.selectionStart = el.selectionEnd = start + 1;
    autoResize(); // (新增) 换行时调整高度
  });
};

defineExpose({
  setContent,
  focus,
  clearInput
});
</script>

<style scoped>
.chat-input-area {
  display: flex;
  flex-direction: column;
  gap: 0.75rem; /* (调整) 选项和输入框的间距 */
  padding: 1rem 1.5rem; /* (调整) */
  border-top: 1px solid var(--border-color);
  background-color: var(--card-bg); /* (新增) 底部背景 */
  flex-shrink: 0;
}

/* (调整) 选项样式 */
.chat-options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
}

.option-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius);
  transition: all 0.2s ease;
  user-select: none;
}

.option-label:hover {
  background-color: var(--bg-color);
}

.option-label .icon-small {
  width: 1rem;
  height: 1rem;
  color: var(--text-light);
  transition: color 0.2s ease;
}

/* (新增) 隐藏默认 checkbox */
.custom-checkbox {
  display: none;
}

/* (新增) 自定义 checkbox 图标/状态 */
.checkbox-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
}

/* (新增) 选中状态 */
.custom-checkbox:checked + .checkbox-icon .icon-small {
  color: var(--primary-color);
}
.custom-checkbox:checked ~ span {
  color: var(--primary-color);
  font-weight: 500;
}


/* (调整) 输入框包装器 */
.input-wrapper {
  display: flex;
  align-items: flex-end; /* (调整) 底部对齐 */
  gap: 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  background-color: var(--card-bg); /* 确保背景色 */
  padding: 0.5rem 0.5rem 0.5rem 0.75rem; /* (调整) 内边距 */
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.input-wrapper.focused {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.chat-input {
  flex: 1;
  border: none;
  padding: 0.25rem 0; /* (调整) 优化 padding */
  font-size: 0.95rem; /* (调整) */
  background-color: transparent;
  resize: none;
  overflow-y: auto; /* (新增) */
  max-height: 200px; /* (新增) 最大高度 */
  line-height: 1.5;
  box-shadow: none;
}

.chat-input:focus {
  outline: none;
  border: none;
  box-shadow: none;
}
.chat-input::placeholder {
  color: var(--text-light);
  opacity: 0.4;
}

/* (调整) 发送按钮 */
.send-button {
  background-color: var(--primary-color);
  color: white;
  border: none;
  border-radius: var(--radius);
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}

.send-button:hover:not(:disabled) {
  background-color: var(--primary-dark);
}

.send-button:disabled {
  background-color: var(--primary-light);
  opacity: 1;
  cursor: not-allowed;
}

.send-button .icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* (调整) loading 动画 */
.loading {
  width: 1.25rem;
  height: 1.25rem;
  border-color: rgba(255, 255, 255, 0.4);
  border-top-color: white;
  margin: 0;
}
</style>
