<template>
  <div class="chat-input-container">
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
import { ref, defineProps, defineEmits, defineExpose, nextTick } from 'vue';

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
});

const emits = defineEmits(['send']);

const message = ref('');
const textareaRef = ref(null);

// (新增) 暴露方法供父组件调用
const setContent = (content) => {
  message.value = content || '';
};

// (新增) 聚焦输入框
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

// (新增) 暴露方法
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
