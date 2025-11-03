<template>
  <div class="chat-input-container">
    <!-- (新增) 搜索选项开关 -->
    <div class="chat-options">
      <label class="option-label" for="db-search-toggle">
        <input
          type="checkbox"
          id="db-search-toggle"
          v-model="useDbSearch"
        />
        <span>数据库查询</span>
      </label>
      <label class="option-label" for="web-search-toggle">
        <input
          type="checkbox"
          id="web-search-toggle"
          v-model="useWebSearch"
        />
        <span>联网搜索</span>
      </label>
    </div>

    <textarea
      ref="textareaRef"
      v-model="message"
      class="chat-input"
      placeholder="输入消息..."
      @keyup.enter.exact="sendMessage"
      @keyup.enter.shift="addNewline"
      :disabled="loading"
    ></textarea>
    <div class="input-actions">
      <button 
        class="secondary" 
        @click="clearInput"
        :disabled="!message.trim() || loading"
      >
        清除
      </button>
      <button 
        class="primary" 
        @click="sendMessage"
        :disabled="!message.trim() || loading"
      >
        <span v-if="loading" class="loading"></span>
        <span v-else>发送</span>
      </button>
    </div>
  </div>
</template>

<script setup>
// (新增) 导入 computed 和 useStore
import { ref, defineProps, defineEmits, defineExpose, nextTick, computed } from 'vue';
import { useStore } from '../store';

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
});

const emits = defineEmits(['send']);

const message = ref('');
const textareaRef = ref(null);

// (新增) Pinia store
const store = useStore();

// (新增) 计算属性绑定到 store
const useDbSearch = computed({
  get: () => store.useDbSearch,
  set: (value) => store.setUseDbSearch(value)
});

const useWebSearch = computed({
  get: () => store.useWebSearch,
  set: (value) => store.setUseWebSearch(value)
});

const setContent = (content) => {
  message.value = content || '';
};

const focus = () => {
  // 使用 ref 获取 textarea 元素并聚焦
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.focus();
      // 将光标移到文本末尾
      textareaRef.value.setSelectionRange(
        textareaRef.value.value.length, 
        textareaRef.value.value.length
      );
    }
  });
};

const sendMessage = () => {
  const content = message.value.trim();
  if (content) {
    emits('send', content);
    message.value = '';
  }
};

const clearInput = () => {
  message.value = '';
};

const addNewline = () => {
  message.value += '\n';
};

defineExpose({
  setContent,
  focus,
  clearInput
});
</script>

<style scoped>
.chat-input-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid var(--border-color);
}

/* (新增) 选项样式 */
.chat-options {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.option-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.option-label input {
  cursor: pointer;
}


.chat-input {
  min-height: 80px;
  resize: vertical;
  width: 100%;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.loading {
  margin-right: 0.5rem;
  vertical-align: middle;
}
</style>
