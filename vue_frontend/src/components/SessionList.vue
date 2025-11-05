<template>
  <div class="session-list">
    <div class="session-list-header">
      <h2>会话</h2>
      <!-- (调整) 按钮样式 -->
      <button class="icon-button" @click="showNewSessionDialog = true" title="新建会话">
        <plus-icon class="icon" />
      </button>
    </div>
    <!-- (新增) 搜索输入框 -->
    <div class="session-list-search">
      <search-icon class="search-icon" />
      <input
        type="text"
        v-model="searchQuery"
        placeholder="搜索会话..."
        aria-label="搜索会话"
      />
      <button v-if="searchQuery" @click="clearSearch" class="clear-search-btn icon-button" title="清除搜索">
        <x-icon class="icon" />
      </button>
    </div>
    
    <!-- (新增) 无搜索结果提示 -->
    <div v-if="filteredSessions.length === 0 && searchQuery" class="no-results">
      没有找到匹配的会话。
    </div>
    <!-- (修改) 遍历 filteredSessions -->
    <div class="session-items">
      <div
        v-for="session in filteredSessions"
        :key="session"
        class="session-item"
        :class="{ active: session === currentSession }"
        @click="selectSession(session)"
      >
        <span class="session-name">{{ session }}</span>
        <button 
          class="delete-btn icon-button" 
          @click.stop="deleteSession(session)"
          title="删除会话"
        >
          <trash-icon class="icon" />
        </button>
      </div>
    </div>
    
    <!-- (调整) 新建会话对话框样式 -->
    <div v-if="showNewSessionDialog" class="dialog-overlay" @click.self="showNewSessionDialog = false">
      <div class="dialog card">
        <h3>新建会话</h3>
        <p>请输入新会话的名称。</p>
        <input
          ref="newSessionInputRef"
          type="text"
          v-model="newSessionName"
          placeholder="例如：故障日志-2023-11-04"
          @keyup.enter="createSession"
        />
        <div class="dialog-buttons">
          <button class="secondary" @click="showNewSessionDialog = false">取消</button>
          <button class="primary" @click="createSession" :disabled="!newSessionName.trim()">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits, watch, nextTick, computed } from 'vue'; // (新增) watch, nextTick
import { PlusIcon, TrashIcon, SearchIcon, XIcon } from 'vue-tabler-icons';

const props = defineProps({
  sessions: {
    type: Array,
    required: true
  },
  currentSession: {
    type: String,
    required: true
  }
});

const emits = defineEmits(['select', 'delete', 'create']);

const showNewSessionDialog = ref(false);
const newSessionName = ref('');
const newSessionInputRef = ref(null); // (新增) input 引用
// (新增) 搜索相关 state
const searchQuery = ref('');

// (新增) 监听弹窗显示，自动聚焦
watch(showNewSessionDialog, (isShown) => {
  if (isShown) {
    nextTick(() => {
      newSessionInputRef.value?.focus();
    });
  }
});

// (新增) 过滤会话列表的计算属性
const filteredSessions = computed(() => {
  if (!searchQuery.value) {
    return props.sessions; // 如果搜索框为空，显示所有会话
  }
  const lowerCaseQuery = searchQuery.value.toLowerCase();
  return props.sessions.filter(session =>
    session.toLowerCase().includes(lowerCaseQuery)
  );
});
const selectSession = (session) => {
  emits('select', session);
};

// (修改) 替换 confirm
const deleteSession = (session) => {
  if (window.confirm(`确定要删除会话 "${session}" 吗？`)) {
    emits('delete', session);
  }
};

const createSession = () => {
  if (newSessionName.value.trim()) {
    emits('create', newSessionName.value.trim());
    newSessionName.value = '';
    showNewSessionDialog.value = false;
  }
};

// (新增) 清除搜索关键词
const clearSearch = () => {
  searchQuery.value = '';
};

</script>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  flex: 1; /* (新增) 占据剩余空间 */
  overflow: hidden; /* (新增) */
}

.session-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1rem 0.5rem 1.5rem; /* (调整) padding */
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.session-list-header h2 {
  font-size: 1rem; /* (调整) */
  font-weight: 600;
  text-transform: uppercase; /* (新增) 大写 */
  color: var(--text-secondary);
}

/* (新增) 图标按钮通用样式 */
.icon-button {
  background: none;
  border: none;
  padding: 0.375rem;
  border-radius: var(--radius);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.icon-button:hover {
  background-color: var(--bg-color);
  color: var(--text-primary);
}

.icon {
  width: 1.25rem;
  height: 1.25rem;
  display: block; /* (新增) */
}


/* (新增) 搜索框样式 */
.session-list-search {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--bg-color-light); /* 稍微区分背景 */
  flex-shrink: 0;
}

.session-list-search .search-icon {
  width: 1.125rem;
  height: 1.125rem;
  color: var(--text-secondary);
  margin-right: 0.5rem;
  flex-shrink: 0;
}

.session-list-search input {
  flex-grow: 1;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
  background-color: var(--bg-color);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.2s ease;
}

.session-list-search input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.session-list-search .clear-search-btn {
  margin-left: 0.5rem;
  color: var(--text-secondary);
  padding: 0.25rem;
}

.session-list-search .clear-search-btn:hover {
  background-color: var(--bg-color);
  color: var(--text-primary);
}

/* (新增) 无结果提示样式 */
.no-results {
  padding: 1rem;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.9rem;
  flex-grow: 1; /* 占据剩余空间 */
  display: flex;
  align-items: center;
  justify-content: center;
}

.session-items {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem; /* (调整) */
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.625rem 0.75rem; /* (调整) */
  border-radius: var(--radius);
  margin-bottom: 0.25rem; /* (调整) */
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  user-select: none;
}

.session-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 0.5rem;
}

.session-item:hover {
  background-color: var(--bg-color);
}

/* (调整) 激活状态样式 */
.session-item.active {
  background-color: var(--primary-light);
}
.session-item.active .session-name {
  color: var(--primary-dark);
  font-weight: 600;
}
.session-item.active .delete-btn {
  color: var(--primary-dark);
}

.delete-btn {
  padding: 0.25rem;
  opacity: 0; /* (调整) 默认隐藏 */
  visibility: hidden;
  transition: opacity 0.2s, visibility 0.2s;
  flex-shrink: 0;
}

.session-item:hover .delete-btn {
  opacity: 0.7;
  visibility: visible;
}
.session-item:hover .delete-btn:hover {
  opacity: 1;
  background-color: var(--border-color);
}

/* (调整) 弹窗样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.4); /* (调整) 调暗 */
  backdrop-filter: blur(2px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

/* (调整) card 样式已在全局定义 */
.dialog {
  width: 100%;
  max-width: 400px;
  padding: 1.5rem;
  animation: dialog-fade-in 0.2s ease;
}

@keyframes dialog-fade-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.dialog h3 {
  margin-bottom: 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}
.dialog p {
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.dialog input {
  width: 100%;
  margin-bottom: 1.5rem;
}

.dialog-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
