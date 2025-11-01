import { defineStore } from 'pinia';

export const useStore = defineStore('main', {
  state: () => ({
    apiKey: localStorage.getItem('apiKey') || null,
    currentSession: localStorage.getItem('currentSession') || 'default_session',
    sessions: JSON.parse(localStorage.getItem('sessions') || '["default_session"]'),
    messages: {}, // (e.g., { 'session_id': [ { id, isUser, content, think_process, duration, timestamp } ] })
    loading: false,
    error: null
  }),

  actions: {
    // 保存API Key
    setApiKey(key) {
      this.apiKey = key;
      localStorage.setItem('apiKey', key);
    },

    // 清除API Key（退出登录）
    clearApiKey() {
      this.apiKey = null;
      localStorage.removeItem('apiKey');
    },

    // 添加新会话
    addSession(sessionId) {
      if (!this.sessions.includes(sessionId)) {
        this.sessions.push(sessionId);
        localStorage.setItem('sessions', JSON.stringify(this.sessions));
      }
      this.setCurrentSession(sessionId);
    },

    // 设置当前会话
    setCurrentSession(sessionId) {
      this.currentSession = sessionId;
      localStorage.setItem('currentSession', sessionId);
    },

    // 删除会话
    removeSession(sessionId) {
      this.sessions = this.sessions.filter(id => id !== sessionId);
      localStorage.setItem('sessions', JSON.stringify(this.sessions));

      // 如果删除的是当前会话，切换到默认会话
      if (sessionId === this.currentSession) {
        const newSession = this.sessions.length > 0 ? this.sessions[0] : 'default_session';
        this.setCurrentSession(newSession);
      }
    },

    // (修改) 保存消息到状态 (现在接收一个 payload 对象)
    addMessage(sessionId, isUser, messagePayload) {
      if (!this.messages[sessionId]) {
        this.messages[sessionId] = [];
      }

      const newMessage = {
        id: Date.now() + Math.random(), // (修改) 增加随机性确保唯一
        isUser,
        content: '', // (修改) 默认空
        think_process: '', // (修改) 默认空
        duration: null, // (修改) 默认 null
        ...messagePayload, // (修改) 覆盖默认值
        timestamp: new Date()
      };

      this.messages[sessionId].push(newMessage);
      return newMessage.id; // (新增) 返回新消息的 ID
    },

    // (新增) 更新最后一条消息 (用于流式)
    updateLastMessage(sessionId, payload) {
      if (!this.messages[sessionId] || this.messages[sessionId].length === 0) {
        return;
      }

      const lastMessageIndex = this.messages[sessionId].length - 1;
      const lastMessage = this.messages[sessionId][lastMessageIndex];

      // (修改) 确保是 AI 消息
      if (lastMessage.isUser) {
        console.error("Trying to update user message (stream)");
        return;
      }

      // (新增) 累积 chunk
      if (payload.content_chunk) {
        lastMessage.content += payload.content_chunk;
      }
      if (payload.think_chunk) {
        // (修复) 确保 think_process 是字符串
        if (lastMessage.think_process === null || lastMessage.think_process === undefined) {
          lastMessage.think_process = "";
        }
        lastMessage.think_process += payload.think_chunk;
      }
      // (新增) 设置最终元数据
      if (payload.duration) {
        lastMessage.duration = payload.duration;
      }
    },


    // (修改) 从历史记录加载消息 (包装成新结构)
    loadHistory(sessionId, history) {
      this.messages[sessionId] = [];

      if (!history) return;

      const lines = history.split('\n');
      let currentMessage = null;

      lines.forEach(line => {
        if (line.startsWith('用户：')) {
          if (currentMessage) {
            // (修改) 包装成对象
            this.addMessage(
              sessionId,
              currentMessage.isUser,
              {
                content: currentMessage.content,
                // (修复) 历史记录没有思考过程
                think_process: null,
                duration: null
              }
            );
          }
          currentMessage = {
            isUser: true,
            content: line.replace('用户：', '').trim()
          };
        } else if (line.startsWith('回复：')) {
          if (currentMessage) {
            // (修改) 包装成对象
            this.addMessage(
              sessionId,
              currentMessage.isUser,
              {
                content: currentMessage.content,
                think_process: null,
                duration: null
              }
            );
          }
          currentMessage = {
            isUser: false,
            content: line.replace('回复：', '').trim()
          };
        }
      });

      if (currentMessage) {
        // (修改) 包装成对象
        this.addMessage(
          sessionId,
          currentMessage.isUser,
          {
            content: currentMessage.content,
            think_process: null,
            duration: null
          }
        );
      }
    },

    // 清空会话消息
    clearSessionMessages(sessionId) {
      this.messages[sessionId] = [];
    },

    // 设置加载状态
    setLoading(state) {
      this.loading = state;
    },

    // 设置错误信息
    setError(message) {
      this.error = message;
      // 3秒后自动清除错误信息
      setTimeout(() => {
        this.error = null;
      }, 3000);
    }
  }
});
