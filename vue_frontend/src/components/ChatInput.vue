<template>
  <div class="chat-input-area">
    <!-- (调整) 搜索选项开关样式 -->
    <div class="chat-options">
      <div class="options-left">
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
        <div v-if="attachmentText" class="attachment-chip" title="此文件内容将作为本次消息附件发送">
          <paperclip-icon class="icon-small" />
          <span>已添加{{ attachmentName }}</span>
          <button class="chip-close" @click="removeAttachment" :disabled="loading" aria-label="移除附件">×</button>
        </div>
      </div>
    </div>

    <!-- (调整) 输入框和按钮的包装器 -->
    <div class="input-wrapper" :class="{ 'focused': isFocused }">
      <!-- 新增：上传文件按钮（触发隐藏文件选择） -->
      <input
        ref="fileInputRef"
        type="file"
        accept=".txt,.docx,.xlsx"
        style="display:none"
        @change="onFileChange"
      />
      <button
        class="send-button"
        style="background-color: var(--bg-color); color: var(--text-color);"
        @click="triggerFileSelect"
        :disabled="loading"
        title="上传并读取文件"
      >
        <paperclip-icon class="icon" />
      </button>
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
import { SendIcon, DatabaseIcon, WorldIcon, PaperclipIcon } from 'vue-tabler-icons';
import apiDefault, { uploadFile as uploadFileApi } from '../api';

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
const fileInputRef = ref(null);
const attachmentText = ref('');
const attachmentName = ref('');

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
    emits('send', content, { attachmentText: attachmentText.value, attachmentName: attachmentName.value });
    message.value = '';
    attachmentText.value = '';
    attachmentName.value = '';
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

// 新增：触发文件选择
const triggerFileSelect = () => {
  if (fileInputRef.value) fileInputRef.value.click();
};

// 新增：处理文件选择并上传解析
const onFileChange = async (e) => {
  const files = e.target.files;
  if (!files || !files[0]) return;
  const file = files[0];
  try {
    const res = await uploadFileApi(file);
    attachmentText.value = res.text || '';
    attachmentName.value = file.name || '附件文本';
  } catch (err) {
    // 简单提示方式：将错误写入输入框开头，方便用户看到
    setContent(`【文件读取失败】${err.message || ''}`);
  } finally {
    e.target.value = '';
  }
};

// 新增：移除附件
const removeAttachment = () => {
  attachmentText.value = '';
  attachmentName.value = '';
};

defineExpose({
  setContent,
  focus,
  clearInput
});
</script>

<style scoped>
.chat-input-area {
  max-width: 100%; /* 确保它能铺满父容器 */
  width: 100%; 
  margin: 0; 
  
  display: flex;
  flex-direction: column;
  gap: 0.75rem; 
  
  /* **修改：左右 padding 设为 3rem，与 messages-container 对齐** */
  padding: 1rem 3rem; 
  padding-bottom: 1.5rem; /* 修正底部留白 */
  
  border-top: 1px solid var(--border-color);
  background-color: var(--card-bg); 
  flex-shrink: 0;
}

/* (调整) 选项样式 */
.chat-options {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  align-items: center;
  justify-content: space-between;
}

.options-left {
  display: inline-flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.options-right {
  display: inline-flex;
  align-items: center;
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
  min-height: 2rem;
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

/* 新增：附件标签样式 */
.attachment-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background-color: var(--bg-color);
  color: var(--text-secondary);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius);
  padding: 0.25rem 0.5rem;
  min-height: 2rem; /* 与 option-label 同高 */
  font-size: 0.875rem; /* 与 option-label 同字号 */
}

.chip-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0 0.25rem;
}

/* 统一附件标签内图标尺寸与颜色，匹配开关图标 */
.attachment-chip .icon-small {
  width: 1rem;
  height: 1rem;
  color: var(--text-light);
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
