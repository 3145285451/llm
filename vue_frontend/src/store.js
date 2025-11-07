import { defineStore } from 'pinia';

export const useStore = defineStore('main', {
  state: () => ({
    apiKey: localStorage.getItem('apiKey') || null,
    currentSession: localStorage.getItem('currentSession') || '默认对话',
    sessions: JSON.parse(localStorage.getItem('sessions') || '["默认对话"]'),
    messages: {}, // (e.g., { 'session_id': [ { id, isUser, content, think_process, duration, timestamp } ] })
    loading: false,
    error: null,
    // (新增) 编辑状态
    isEditing: false,
    editingMessageId: null,

    // (新增) 搜索选项
    useDbSearch: true,
    useWebSearch: false,

    // (新增) 术语词典
    glossary: {}
  }),

  actions: {
    // (新增) 设置搜索选项
    setUseDbSearch(value) {
      this.useDbSearch = value;
    },
    setUseWebSearch(value) {
      this.useWebSearch = value;
    },

    // (新增) 设置术语词典
    setGlossary(entries) {
      this.glossary = entries || {};
    },

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
        const newSession = this.sessions.length > 0 ? this.sessions[0] : '默认对话';
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

    // (新增) 更新指定索引的消息 (用于编辑模式的流式)
    updateMessageAtIndex(sessionId, messageIndex, payload) {
      if (!this.messages[sessionId] || !this.messages[sessionId][messageIndex]) {
        return;
      }

      const message = this.messages[sessionId][messageIndex];

      // (新增) 累积 chunk
      if (payload.content_chunk) {
        if (!message.content) {
          message.content = '';
        }
        message.content += payload.content_chunk;
      }
      if (payload.think_chunk) {
        // (修复) 确保 think_process 是字符串
        if (message.think_process === null || message.think_process === undefined) {
          message.think_process = "";
        }
        message.think_process += payload.think_chunk;
      }
      // (新增) 设置最终元数据
      if (payload.duration) {
        message.duration = payload.duration;
      }
    },

    // (新增) 移除最后一条消息 (用于重新生成)
    removeLastMessage(sessionId) {
      if (!this.messages[sessionId] || this.messages[sessionId].length === 0) {
        return;
      }

      const lastMessage = this.messages[sessionId][this.messages[sessionId].length - 1];

      // 确保最后一条是 AI 消息
      if (!lastMessage.isUser) {
        this.messages[sessionId].pop();
      } else {
        console.warn('Attempted to remove last message, but it was a user message.');
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
    },

    // (新增) 设置编辑状态
    setEditing(messageId) {
      this.isEditing = true;
      this.editingMessageId = messageId;
    },

    // (新增) 清除编辑状态
    clearEditing() {
      this.isEditing = false;
      this.editingMessageId = null;
    },

    // (新增) 替换消息内容和删除后续消息（用于编辑模式的完成）
    replaceMessagesFromIndex(sessionId, startIndex, newUserContent, newAiContent) {
      if (!this.messages[sessionId] || startIndex < 0 || startIndex >= this.messages[sessionId].length) {
        return;
      }

      // 1. 替换用户消息内容
      if (this.messages[sessionId][startIndex].isUser) {
        this.messages[sessionId][startIndex].content = newUserContent;
      }

      // 2. 确保下一条消息是 AI 消息，然后替换其内容
      if (startIndex + 1 < this.messages[sessionId].length) {
        const aiMessage = this.messages[sessionId][startIndex + 1];
        if (!aiMessage.isUser) {
          aiMessage.content = newAiContent || '';
          aiMessage.think_process = '';
          aiMessage.duration = null;
        }
      } else {
        // 如果没有 AI 消息，创建一个
        this.messages[sessionId].push({
          id: Date.now() + Math.random(),
          isUser: false,
          content: newAiContent || '',
          think_process: '',
          duration: null,
          timestamp: new Date()
        });
      }

      // 3. 删除从 startIndex + 2 开始的所有后续消息
      if (startIndex + 2 < this.messages[sessionId].length) {
        this.messages[sessionId].splice(startIndex + 2);
      }
    }
  }
});
