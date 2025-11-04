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
          <!-- (调整) 按钮样式和图标 -->
          <button class="secondary" @click="handleClearHistory">
            <trash-icon class="icon-small" />
            清空当前会话
          </button>
          <button class="secondary danger-hover" @click="handleLogout">
            <logout-icon class="icon-small" />
            退出登录
          </button>
        </div>
      </div>
    </div>
    
    <div class="chat-area">
      <div class="chat-header">
        <!-- (调整) 移除 h1，简化标题 -->
        <h2 class="session-title">{{ currentSession }}</h2>
        <p class="session-subtitle">大模型故障日志诊断</p>
      </div>
      
      <div v-if="error" class="error-message global-error">{{ error }}</div>
      
      <div class="messages-container" ref="messagesContainerRef">
        <div v-if="messages.length === 0" class="empty-state">
          <!-- (新增) 增加图标和欢迎语 -->
          <div class="logo-icon-wrapper">
<svg height="5em" style="flex:none;line-height:1" viewBox="0 0 24 24" width="5em" xmlns="http://www.w3.org/2000/svg"><title>DeepSeek</title><path d="M23.748 4.482c-.254-.124-.364.113-.512.234-.051.039-.094.09-.137.136-.372.397-.806.657-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-.156-.708-.311-.955-.65-.172-.241-.219-.51-.305-.774-.055-.16-.11-.323-.293-.35-.2-.031-.278.136-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.393.137.093.172.187.129.323-.082.28-.18.552-.266.833-.055.179-.137.217-.329.14a5.526 5.526 0 01-1.736-1.18c-.857-.828-1.631-1.742-2.597-2.458a11.365 11.365 0 00-.689-.471c-.985-.957.13-1.743.388-1.836.27-.098.093-.432-.779-.428-.872.004-1.67.295-2.687.684a3.055 3.055 0 01-.465.137 9.597 9.597 0 00-2.883-.102c-1.885.21-3.39 1.102-4.497 2.623C.082 8.606-.231 10.684.152 12.85c.403 2.284 1.569 4.175 3.36 5.653 1.858 1.533 3.997 2.284 6.438 2.14 1.482-.085 3.133-.284 4.994-1.86.47.234.962.327 1.78.397.63.059 1.236-.03 1.705-.128.735-.156.684-.837.419-.961-2.155-1.004-1.682-.595-2.113-.926 1.096-1.296 2.746-2.642 3.392-7.003.05-.347.007-.565 0-.845-.004-.17.035-.237.23-.256a4.173 4.173 0 001.545-.475c1.396-.763 1.96-2.015 2.093-3.517.02-.23-.004-.467-.247-.588zM11.581 18c-2.089-1.642-3.102-2.183-3.52-2.16-.392.024-.321.471-.235.763.09.288.207.486.371.739.114.167.192.416-.113.603-.673.416-1.842-.14-1.897-.167-1.361-.802-2.5-1.86-3.301-3.307-.774-1.393-1.224-2.887-1.298-4.482-.02-.386.093-.522.477-.592a4.696 4.696 0 011.529-.039c2.132.312 3.946 1.265 5.468 2.774.868.86 1.525 1.887 2.202 2.891.72 1.066 1.494 2.082 2.48 2.914.348.292.625.514.891.677-.802.09-2.14.11-3.054-.614zm1-6.44a.306.306 0 01.415-.287.302.302 0 01.2.288.306.306 0 01-.31.307.303.303 0 01-.304-.308zm3.11 1.596c-.2.081-.399.151-.59.16a1.245 1.245 0 01-.798-.254c-.274-.23-.47-.358-.552-.758a1.73 1.73 0 01.016-.588c.07-.327-.008-.537-.239-.727-.187-.156-.426-.199-.688-.199a.559.559 0 01-.254-.078c-.11-.054-.2-.19-.114-.358.028-.054.16-.186.192-.21.356-.202.767-.136 1.146.016.352.144.618.408 1.001.782.391.451.462.576.685.914.176.265.336.537.445.848.067.195-.019.354-.25.452z" fill="#4D6BFE"></path></svg>
          </div>
          <h3>开始您的诊断对话</h3>
          <p>请在下方输入您的问题或日志信息。</p>
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
        
        <div 
          v-if="loading && 
                messages.length > 0 && 
                !messages[messages.length - 1].isUser && 
                !messages[messages.length - 1].content && 
                !messages[messages.length - 1].think_process" 
          class="loading-indicator"
        >
          <div class="loading"></div>
          <p>KAI 正在分析...</p>
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
// (新增) 导入图标
import { onMounted, computed, ref, nextTick } from 'vue'; 
import { useRouter } from 'vue-router';
import { useStore } from '../store';
import api from '../api';
import SessionList from '../components/SessionList.vue';
import ChatMessage from '../components/ChatMessage.vue';
import ChatInput from '../components/ChatInput.vue';
// (新增) 导入图标
import { TrashIcon, LogoutIcon } from 'vue-tabler-icons';

const store = useStore();
const router = useRouter();
const messagesContainerRef = ref(null); 
const chatInputRef = ref(null); 
const lastUserMessage = ref(''); 

// ... (计算属性)
const sessions = computed(() => store.sessions);
const currentSession = computed(() => store.currentSession);
const messages = computed(() => store.messages[currentSession.value] || []);
const loading = computed(() => store.loading);
const error = computed(() => store.error);
const isEditing = computed(() => store.isEditing);
const editingMessageId = computed(() => store.editingMessageId);
const useDbSearch = computed(() => store.useDbSearch);
const useWebSearch = computed(() => store.useWebSearch);


const scrollToBottom = async () => {
  await nextTick();
  const container = messagesContainerRef.value;
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
};

const loadHistory = async (sessionId) => {
  try {
    store.setLoading(true);
    const response = await api.getHistory(sessionId);
    store.loadHistory(sessionId, response.data.history);

    const currentMessages = store.messages[sessionId] || [];
    const lastUserMsg = [...currentMessages].reverse().find(m => m.isUser);
    lastUserMessage.value = lastUserMsg ? lastUserMsg.content : '';

    await scrollToBottom(); 
  } catch (err) {
    store.setError(err.response?.data?.error || '加载历史记录失败');
  } finally {
    store.setLoading(false);
  }
};

onMounted(() => {
  loadHistory(currentSession.value);
});

const handleSelectSession = async (sessionId) => {
  store.setCurrentSession(sessionId);
  await loadHistory(sessionId);
};

const handleDeleteSession = async (sessionId) => {
  try {
    if (store.sessions.length === 1 && store.sessions[0] === sessionId) {
        store.addSession('default_session');
    }
    await api.clearHistory(sessionId);
    store.removeSession(sessionId);
    store.clearSessionMessages(sessionId);
    await loadHistory(store.currentSession);
  } catch (err) {
    store.setError(err.response?.data?.error || '删除会话失败');
  }
};

const handleCreateSession = (sessionId) => {
  store.addSession(sessionId);
  store.clearSessionMessages(sessionId);
  loadHistory(sessionId);
};

const handleSendMessage = async (content) => {
  const sessionId = currentSession.value;

  if (isEditing.value && editingMessageId.value) {
    await handleEditSend(sessionId, content);
  } else {
    await handleNormalSend(sessionId, content);
  }
};

const handleNormalSend = async (sessionId, content) => {
  lastUserMessage.value = content;
  store.addMessage(sessionId, true, { content: content });
  await scrollToBottom(); 
  
  const aiMessageId = store.addMessage(sessionId, false, { 
    content: '', 
    think_process: '' 
  });
  await scrollToBottom(); 
  
  store.setLoading(true);
  store.setError(null);

  await api.streamChat(
    sessionId,
    content,
    (data) => {
      if (data.type === 'content') {
        store.updateLastMessage(sessionId, { content_chunk: data.chunk });
      } else if (data.type === 'think') {
        store.updateLastMessage(sessionId, { think_chunk: data.chunk });
      } else if (data.type === 'metadata') {
        store.updateLastMessage(sessionId, { duration: data.duration });
      } else if (data.type === 'error') {
        store.setError(data.chunk || '流式响应出错');
      }
      scrollToBottom();
    },
    (errorMessage) => {
      store.setLoading(false);
      store.setError(errorMessage);
      scrollToBottom();
    },
    () => {
      store.setLoading(false);
      scrollToBottom();
    },
    null, 
    useDbSearch.value,
    useWebSearch.value
  );
};

const handleEditSend = async (sessionId, editedContent) => {
  const messageId = editingMessageId.value;
  const chatHistory = messages.value;

  lastUserMessage.value = editedContent;
  
  const editIndex = chatHistory.findIndex(msg => msg.id === messageId);
  
  if (editIndex === -1) {
    store.setError('找不到要编辑的消息');
    store.clearEditing();
    return;
  }

  const context = chatHistory.slice(0, editIndex).map(msg => ({
    role: msg.isUser ? 'user' : 'assistant',
    content: msg.content
  }));

  chatHistory[editIndex].content = editedContent;

  let aiMessageIndex = editIndex + 1;
  
  if (aiMessageIndex >= chatHistory.length) {
    store.addMessage(sessionId, false, { 
      content: '', 
      think_process: '' 
    });
    aiMessageIndex = editIndex + 1;
  } else if (chatHistory[aiMessageIndex].isUser) {
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
    chatHistory[aiMessageIndex].content = '';
    chatHistory[aiMessageIndex].think_process = '';
    chatHistory[aiMessageIndex].duration = null;
  }

  if (editIndex + 2 < chatHistory.length) {
    chatHistory.splice(editIndex + 2);
  }

  await scrollToBottom();
  store.setLoading(true);
  store.setError(null);

  await api.streamChat(
    sessionId,
    editedContent,
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
      scrollToBottom();
    },
    (errorMessage) => {
      store.setLoading(false);
      store.setError(errorMessage);
      store.clearEditing();
      scrollToBottom();
    },
    () => {
      store.setLoading(false);
      store.clearEditing();
      if (chatInputRef.value) {
        chatInputRef.value.clearInput();
      }
      scrollToBottom();
    },
    context,
    useDbSearch.value,
    useWebSearch.value
  );
};

const handleRegenerate = async () => {
  if (loading.value || !lastUserMessage.value) {
    console.warn('Cannot regenerate while loading or no last user message.');
    return;
  }
  const sessionId = currentSession.value;
  
  const currentMessages = messages.value;
  if (currentMessages.length === 0 || currentMessages[currentMessages.length - 1].isUser) {
      console.warn('Last message is not an AI message.');
      return;
  }

  store.removeLastMessage(sessionId);
  await scrollToBottom(); 
  
  await handleNormalSend(sessionId, lastUserMessage.value);
};

const handleEditMessage = (editData) => {
  const { messageId, content } = editData;
  store.setEditing(messageId);
  
  if (chatInputRef.value) {
    chatInputRef.value.setContent(content);
  }
  
  scrollToBottom();
  nextTick(() => {
    if (chatInputRef.value) {
      chatInputRef.value.focus();
    }
  });
};

// (修改) 替换 confirm
const handleClearHistory = async () => {
  if (window.confirm(`确定要清空当前会话 "${currentSession.value}" 的历史记录吗？`)) {
    try {
      await api.clearHistory(currentSession.value);
      store.clearSessionMessages(currentSession.value);
      await scrollToBottom();
    } catch (err)
 {
      store.setError(err.response?.data?.error || '清空历史记录失败');
    }
  }
};

// (修改) 替换 confirm
const handleLogout = () => {
  if (window.confirm('确定要退出登录吗？')) {
    store.clearApiKey();
    router.push('/login');
  }
};
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  overflow: hidden; /* (新增) 防止溢出 */
}

.sidebar {
  width: 280px; /* (调整) 宽度 */
  flex-shrink: 0; /* (新增) 防止侧边栏被压缩 */
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
  flex-direction: column; /* (调整) 垂直排列 */
  gap: 0.5rem;
}

.user-actions button {
  width: 100%;
  justify-content: flex-start; /* (新增) 按钮内容左对齐 */
  font-size: 0.875rem;
}

/* (新增) 退出登录按钮的悬停效果 */
.danger-hover:hover {
  background-color: #fee2e2;
  border-color: #fca5a5;
  color: var(--danger-color);
}

.icon-small {
  width: 1rem;
  height: 1rem;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
  overflow: hidden; 
}

.chat-header {
  padding: 1rem 1.5rem; /* (调整) 增加 padding */
  background-color: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.session-title {
  font-size: 1.25rem; /* (调整) */
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.session-subtitle {
  font-size: 0.875rem; /* (调整) */
  color: var(--text-secondary);
  font-weight: 500;
  margin: 0;
}

/* (新增) 全局错误提示定位 */
.global-error {
  margin: 1rem 1.5rem 0;
  box-shadow: var(--shadow);
}

.messages-container {
  flex: 1;
  padding: 1.5rem; /* (调整) 增加 padding */
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem; /* (调整) 消息间距 */
}

/* (调整) 空状态样式 */
.empty-state {
  margin: auto;
  color: var(--text-secondary);
  font-size: 1rem;
  text-align: center;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.logo-icon-wrapper {
  border-radius: 50%;
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: var(--primary-color);
}

.empty-state h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem; /* (调整) */
  padding: 0.5rem 1rem;
  color: var(--text-secondary);
  font-size: 0.9rem;
  max-width: 80%;
  align-self: flex-start;
}

.loading-indicator .loading {
  width: 1.25rem;
  height: 1.25rem;
}
</style>
