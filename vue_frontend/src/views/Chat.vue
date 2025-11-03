<template>
  <div class="chat-container">
    <div class="sidebar">
      <SessionList
        :sessions="sessions"
        :current-session="currentSession"
        @select="handleSelectSession"
        @delete="handleDeleteSession"
        @create="handleCreateSession"
      />
      
      <div class="user-info">
        <div class="user-actions">
          <button class="secondary" @click="handleClearHistory">
            清空当前会话
          </button>
          <button class="danger" @click="handleLogout">
            退出登录
          </button>
        </div>
      </div>
    </div>
    
    <div class="chat-area">
      <div class="chat-header">
        <h1>DeepSeek-KAI.v.0.0.1 聊天</h1>
        <h2>当前会话: {{ currentSession }}</h2>
      </div>
      
      <div v-if="error" class="error-message">{{ error }}</div>
      
      <div class="messages-container" ref="messagesContainerRef"> <!-- ref -->
        <div v-if="messages.length === 0" class="empty-state">
          开始与 DeepSeek-KAI.v.0.0.1 的对话吧！
        </div>
        
        <ChatMessage
          v-for="(msg, index) in messages"
          :key="msg.id"
          :is-user="msg.isUser"
          :content="msg.content"
          :think-process="msg.think_process" 
          :duration="msg.duration"
          :timestamp="msg.timestamp"
          :message-id="msg.id"
          :allow-regenerate="!msg.isUser && index === messages.length - 1 && !loading"
          @regenerate="handleRegenerate"
          @edit="handleEditMessage"
        />
        
        <!-- loading-indicator 的 v-if 条件 -->
        <!-- 仅当 loading=true 且最后一条 (AI) 消息完全为空时显示 -->
        <div 
          v-if="loading && 
                messages.length > 0 && 
                !messages[messages.length - 1].isUser && 
                !messages[messages.length - 1].content && 
                !messages[messages.length - 1].think_process" 
          class="loading-indicator"
        >
          <div class="loading"></div>
          <p>DeepSeek-KAI.v.0.0.1 正在思考...</p>
        </div>
      </div>
      
      <ChatInput
        ref="chatInputRef"
        :loading="loading"
        @send="handleSendMessage"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, computed, ref, nextTick } from 'vue'; // ref, nextTick
import { useRouter } from 'vue-router';
import { useStore } from '../store';
import api from '../api';
import SessionList from '../components/SessionList.vue';
import ChatMessage from '../components/ChatMessage.vue';
import ChatInput from '../components/ChatInput.vue';

const store = useStore();
const router = useRouter();
const messagesContainerRef = ref(null); // 消息容器引用
const chatInputRef = ref(null); // 聊天输入框引用
const lastUserMessage = ref(''); // 存储最后的用户输入

// 计算属性
const sessions = computed(() => store.sessions);
const currentSession = computed(() => store.currentSession);
const messages = computed(() => store.messages[currentSession.value] || []);
const loading = computed(() => store.loading);
const error = computed(() => store.error);
const isEditing = computed(() => store.isEditing);
const editingMessageId = computed(() => store.editingMessageId);

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick(); // 等待 DOM 更新
  const container = messagesContainerRef.value;
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
};

// 初始化加载历史记录
const loadHistory = async (sessionId) => {
  try {
    store.setLoading(true);
    const response = await api.getHistory(sessionId);
    store.loadHistory(sessionId, response.data.history);

    // 加载历史后，找到最后的用户消息
    const currentMessages = store.messages[sessionId] || [];
    const lastUserMsg = [...currentMessages].reverse().find(m => m.isUser);
    lastUserMessage.value = lastUserMsg ? lastUserMsg.content : '';

    await scrollToBottom(); // 加载后滚动
  } catch (err) {
    store.setError(err.response?.data?.error || '加载历史记录失败');
  } finally {
    store.setLoading(false);
  }
};

// 挂载时加载当前会话历史
onMounted(() => {
  loadHistory(currentSession.value);
});

// 处理选择会话
const handleSelectSession = async (sessionId) => {
  store.setCurrentSession(sessionId);
  await loadHistory(sessionId);
};

// 处理删除会话
const handleDeleteSession = async (sessionId) => {
  try {
    // (修复) 确保默认会话存在
    if (store.sessions.length === 1 && store.sessions[0] === sessionId) {
        store.addSession('default_session');
    }
    await api.clearHistory(sessionId);
    store.removeSession(sessionId); // store.removeSession 会自动切换会话
    store.clearSessionMessages(sessionId);
    await loadHistory(store.currentSession); // 加载新会话的历史
  } catch (err) {
    store.setError(err.response?.data?.error || '删除会话失败');
  }
};

// 处理创建会话
const handleCreateSession = (sessionId) => {
  store.addSession(sessionId);
  store.clearSessionMessages(sessionId);
  // 创建后立即加载（空）历史
  loadHistory(sessionId);
};

// 处理发送消息 (流式)
const handleSendMessage = async (content) => {
  const sessionId = currentSession.value;

  // 步骤二：检查是否为编辑模式
  if (isEditing.value && editingMessageId.value) {
    // 步骤三：编辑模式的发送逻辑
    await handleEditSend(sessionId, content);
  } else {
    // 正常模式的发送逻辑
    await handleNormalSend(sessionId, content);
  }
};

// 正常发送模式
const handleNormalSend = async (sessionId, content) => {
  // 存储最后的用户输入
  lastUserMessage.value = content;

  // 1. 添加用户消息
  store.addMessage(sessionId, true, { content: content });
  await scrollToBottom(); // 滚动
  
  // 2. 添加一个空的 AI 回复消息
  const aiMessageId = store.addMessage(sessionId, false, { 
    content: '', 
    think_process: '' 
  });
  await scrollToBottom(); // 滚动
  
  store.setLoading(true);
  store.setError(null);

  // 3. 调用流式 API
  await api.streamChat(
    sessionId,
    content,
    // (onData) 接收 SSE 数据块 (JSON 对象)
    (data) => {
      // 方案 5：后端已解析
      if (data.type === 'content') {
        store.updateLastMessage(sessionId, { content_chunk: data.chunk });
      } else if (data.type === 'think') {
        store.updateLastMessage(sessionId, { think_chunk: data.chunk });
      } else if (data.type === 'metadata') {
        store.updateLastMessage(sessionId, { duration: data.duration });
      } else if (data.type === 'error') {
        store.setError(data.chunk || '流式响应出错');
      }
      scrollToBottom(); // 流式滚动
    },
    // (onError)
    (errorMessage) => {
      store.setLoading(false);
      store.setError(errorMessage);
      scrollToBottom(); // 滚动
    },
    // (onComplete)
    () => {
      store.setLoading(false);
      scrollToBottom(); // 滚动
    }
  );
};

// 编辑模式的发送逻辑（步骤三和四）
const handleEditSend = async (sessionId, editedContent) => {
  const messageId = editingMessageId.value;
  const chatHistory = messages.value;

  // 存储最后的用户输入（用于重新生成功能）
  lastUserMessage.value = editedContent;

  // 步骤三：发送逻辑
  
  // 1. 找到编辑消息的索引
  const editIndex = chatHistory.findIndex(msg => msg.id === messageId);
  
  if (editIndex === -1) {
    store.setError('找不到要编辑的消息');
    store.clearEditing();
    return;
  }

  // 2. 创建截断后的上下文数组（只包含编辑消息之前的所有对话）
  // 格式化为后端需要的格式：{ role: 'user'/'assistant', content: '...' }
  const context = chatHistory.slice(0, editIndex).map(msg => ({
    role: msg.isUser ? 'user' : 'assistant',
    content: msg.content
  }));

  // 3. 替换编辑消息的内容（步骤四：更新聊天记录的第一部分）
  chatHistory[editIndex].content = editedContent;

  // 4. 确保下一条消息是空的 AI 消息（用于接收流式响应）
  let aiMessageIndex = editIndex + 1;
  
  if (aiMessageIndex >= chatHistory.length) {
    // 如果不存在下一条消息，创建新的 AI 消息
    store.addMessage(sessionId, false, { 
      content: '', 
      think_process: '' 
    });
    aiMessageIndex = editIndex + 1;
  } else if (chatHistory[aiMessageIndex].isUser) {
    // 如果下一条是用户消息（不应该发生），插入 AI 消息
    chatHistory.splice(aiMessageIndex, 0, {
      id: Date.now() + Math.random(),
      isUser: false,
      content: '',
      think_process: '',
      duration: null,
      timestamp: new Date()
    });
    aiMessageIndex = editIndex + 1;
  } else {
    // 是 AI 消息，清空其内容用于接收新的流式响应
    chatHistory[aiMessageIndex].content = '';
    chatHistory[aiMessageIndex].think_process = '';
    chatHistory[aiMessageIndex].duration = null;
  }

  // 5. 删除从 editIndex + 2 开始的所有后续消息（步骤四：删除旧分支）
  if (editIndex + 2 < chatHistory.length) {
    chatHistory.splice(editIndex + 2);
  }

  await scrollToBottom();
  store.setLoading(true);
  store.setError(null);

  // 6. 调用流式 API，传入截断后的上下文
  await api.streamChat(
    sessionId,
    editedContent,
    // (onData) 接收 SSE 数据块 (JSON 对象) - 更新特定索引的 AI 消息（步骤四：接收逻辑）
    (data) => {
      if (data.type === 'content') {
        store.updateMessageAtIndex(sessionId, aiMessageIndex, { content_chunk: data.chunk });
      } else if (data.type === 'think') {
        store.updateMessageAtIndex(sessionId, aiMessageIndex, { think_chunk: data.chunk });
      } else if (data.type === 'metadata') {
        store.updateMessageAtIndex(sessionId, aiMessageIndex, { duration: data.duration });
      } else if (data.type === 'error') {
        store.setError(data.chunk || '流式响应出错');
      }
      scrollToBottom(); // 流式滚动
    },
    // (onError)
    (errorMessage) => {
      store.setLoading(false);
      store.setError(errorMessage);
      store.clearEditing(); // 清除编辑状态
      scrollToBottom();
    },
    // (onComplete) - 步骤四：接收逻辑的清理
    () => {
      store.setLoading(false);
      // 清理编辑状态
      store.clearEditing();
      // 清空输入框
      if (chatInputRef.value) {
        chatInputRef.value.clearInput();
      }
      scrollToBottom();
    },
    // 传入上下文
    context
  );
};

// 处理重新生成
const handleRegenerate = async () => {
  if (loading.value || !lastUserMessage.value) {
    console.warn('Cannot regenerate while loading or no last user message.');
    return;
  }
  const sessionId = currentSession.value;
  
  // 1. 确保最后一条是 AI 消息
  const currentMessages = messages.value;
  if (currentMessages.length === 0 || currentMessages[currentMessages.length - 1].isUser) {
      console.warn('Last message is not an AI message.');
      return;
  }

  // 2. 删除最后一条 AI 消息
  store.removeLastMessage(sessionId);
  await scrollToBottom(); // 滚动，隐藏刚删除的消息
  
  // 3. 重新发送
  await handleSendMessage(lastUserMessage.value);
};

// 处理编辑消息
const handleEditMessage = (editData) => {
  const { messageId, content } = editData;
  
  // 1. 设置编辑状态
  store.setEditing(messageId);
  
  // 2. 将输入框内容替换为该消息的文本
  if (chatInputRef.value) {
    chatInputRef.value.setContent(content);
  }
  
  // 3. 滚动到底部，聚焦输入框
  scrollToBottom();
  nextTick(() => {
    if (chatInputRef.value) {
      chatInputRef.value.focus();
    }
  });
};

// 处理清空历史
const handleClearHistory = async () => {
  if (confirm(`确定要清空当前会话 "${currentSession.value}" 的历史记录吗？`)) {
    try {
      await api.clearHistory(currentSession.value);
      store.clearSessionMessages(currentSession.value);
      await scrollToBottom(); // 滚动
    } catch (err)
 {
      store.setError(err.response?.data?.error || '清空历史记录失败');
    }
  }
};

// 处理退出登录
const handleLogout = () => {
  if (confirm('确定要退出登录吗？')) {
    store.clearApiKey();
    router.push('/login');
  }
};
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 300px;
  display: flex;
  flex-direction: column;
  background-color: var(--card-bg);
  border-right: 1px solid var(--border-color);
}

.user-info {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
}

.user-actions {
  display: flex;
  gap: 0.5rem;
}

/* 确保按钮换行 */
.user-actions button {
  flex: 1;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
  /* 防止聊天区溢出 */
  overflow: hidden;
}

.chat-header {
  padding: 1rem;
  background-color: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
}

.chat-header h1 {
  color: var(--primary-color);
  margin-bottom: 0.25rem;
}

.chat-header h2 {
  font-size: 1rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.messages-container {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.empty-state {
  margin: auto;
  color: var(--text-secondary);
  font-size: 1.25rem;
  text-align: center;
  padding: 2rem;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  /* 调整位置 */
  padding: 0.5rem 1rem;
  color: var(--text-secondary);
  max-width: 80%;
  align-self: flex-start; /* 对齐 AI 消息 */
}
</style>
