import axios from 'axios';

// (修改) 保留 axios 用于非流式请求
const axiosApi = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// (修改) axios 拦截器
axiosApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('apiKey');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

axiosApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // 未授权，清除token并跳转到登录页
      localStorage.removeItem('apiKey');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);


// (修改) 流式聊天 API，添加搜索选项
async function streamChat(sessionId, userInput, onData, onError, onComplete, context = null, useDbSearch, useWebSearch) {
  const token = localStorage.getItem('apiKey');

  try {
    const body = {
      session_id: sessionId,
      user_input: userInput,
      use_db_search: useDbSearch,   // (新增)
      use_web_search: useWebSearch, // (新增)
    };

    // (新增) 如果提供了 context，添加到请求体
    if (context && Array.isArray(context) && context.length > 0) {
      body.context = context;
    }

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      // (修改) 处理 HTTP 错误 (假设错误是非流式的)
      try {
        const errorText = await response.text();
        // 尝试解析 SSE 错误
        if (errorText.includes("data:")) {
          const errorData = JSON.parse(errorText.substring(errorText.indexOf('data:') + 5));
          throw new Error(errorData.chunk || `HTTP error! status: ${response.status}`);
        }
        // 尝试解析 JSON 错误
        const errorData = JSON.parse(errorText);
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      } catch (e) {
        throw new Error(e.message || `HTTP error! status: ${response.status}`);
      }
    }

    if (!response.body) {
      throw new Error('Response body is null');
    }

    // (修改) 使用 TextDecoderStream 来处理流
    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        // (修改) 流结束时调用 onComplete
        if (onComplete) onComplete();
        break;
      }

      buffer += value;

      // (新增) 解析 SSE (data: {...}\n\n)
      let eolIndex;
      // (修改) 循环解析缓冲区中的所有 SSE 消息
      while ((eolIndex = buffer.indexOf('\n\n')) !== -1) {
        const line = buffer.substring(0, eolIndex).trim();
        buffer = buffer.substring(eolIndex + 2); // (修改) 移除已处理的消息

        if (line.startsWith('data:')) {
          const dataStr = line.substring(5).trim();
          try {
            const data = JSON.parse(dataStr);

            // (修改) 调用 onData 回调
            if (onData) onData(data);

            // (新增) 如果是 metadata (流结束标志)，调用 onComplete
            if (data.type === 'metadata') {
              if (onComplete) onComplete(data.duration); // (修改) 传递 duration
            }

          } catch (e) {
            console.error('Failed to parse SSE data:', dataStr, e);
            // (修改) 调用 onError 回调
            if (onError) onError('Failed to parse stream data');
          }
        }
      }
    }
  } catch (err) {
    console.error('Fetch stream chat failed:', err);
    // (修改) 调用 onError 回调
    if (onError) onError(err.message || 'Failed to send message');
  }
}


export default {
  // (修改) 保留 axios
  login(username, password) {
    return axiosApi.post('/login', { username, password });
  },

  // (修改) 导出一个新方法
  streamChat, // (新增)

  // (修改) 保留 axios
  getHistory(sessionId) {
    return axiosApi.get('/history', { params: { session_id: sessionId } });
  },

  // (修改) 保留 axios
  clearHistory(sessionId) {
    return axiosApi.delete('/history', { params: { session_id: sessionId } });
  },

  getGlossary() {
    return axiosApi.get('/glossary');
  }
};

// 新增：文件上传 API（返回解析后的纯文本）
export async function uploadFile(file) {
  const token = localStorage.getItem('apiKey');
  const form = new FormData();
  form.append('file', file);

  const resp = await fetch('/api/upload_file', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: form
  });

  if (!resp.ok) {
    const txt = await resp.text();
    try {
      const data = JSON.parse(txt);
      throw new Error(data.error || '文件上传失败');
    } catch {
      throw new Error('文件上传失败');
    }
  }

  return resp.json();
}