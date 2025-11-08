# DeepSeek-R1 故障诊断系统

一个基于大语言模型的智能故障诊断系统，专为解决各类技术问题而设计。该系统结合了 DeepSeek-R1、Qwen3 和 Llama3 等大语言模型，以及向量检索和联网搜索功能，能够帮助用户快速诊断和解决各种技术故障。

---

## 📌 项目概述

本项目是一个集成了大语言模型的故障诊断系统，主要面向开发者和技术支持人员，能够协助诊断各种技术问题，包括但不限于：

- Linux 系统故障  
- 网络设备问题  
- Windows 系统错误  
- 数据库异常  
- 应用服务器问题  
- 编程语言相关错误  

系统采用前后端分离架构，后端基于 Django + Ninja 框架，前端基于 Vue.js 构建。

---

## 🚀 功能特性概述

- 🤖 多模型支持：支持 DeepSeek-R1、Qwen3、Llama3 等多种大语言模型  
- 🔍 智能检索：集成向量检索系统，能够从历史日志中检索相关信息  
- 🌐 联网搜索：支持实时联网搜索，获取最新解决方案  
- 💬 对话式交互：支持上下文理解和多轮对话，提供流畅交互体验  
- 📚 术语解释：悬停显示专业术语词义  
- 📝 会话管理：支持多会话创建、切换、清空
- 🔍 会话搜索：支持在会话列表中搜索特定会话
- 📋 代码操作：支持代码块一键复制、在线运行 HTML/JavaScript 代码
- 📤 文件上传：支持 `.txt`、`.docx`、`.xlsx` 文件进行分析  
- 🧠 思维链展示：可视化展示模型的思考过程  
- 📄 导出功能：会话记录可导出为 HTML 文件  
- 🖥️ HTML实时渲染：支持 Markdown 渲染、代码高亮、在线运行代码片段  
- 🔧 搜索选项控制：可选择启用/禁用数据库查询和联网搜索功能

---

## 🧠 核心特性实现

### 1. 前端文本显示优化
为了提升用户体验，我们对前端文本显示进行了优化：

- 支持 Markdown 格式渲染，使文本更易于阅读
- 代码块高亮显示，便于查看技术内容
- 支持表格、列表等富文本格式
- 响应式设计，适配不同屏幕尺寸

**实现机制：**

- 使用 marked 库将 Markdown 文本解析为 HTML
- 集成 highlight.js 实现代码块语法高亮
- 通过 v-html 指令将渲染后的 HTML 插入到 DOM 中
- 在消息组件更新后自动应用语法高亮

### 2. 科学精准的 Prompt 设计
系统采用精心设计的 Prompt 模板来引导大模型进行数据分析：

- 分层 Prompt 设计，先分析问题再提供解决方案
- 结构化思维链（Chain-of-Thought）引导模型逐步推理
- 上下文感知的动态 Prompt 生成
- 领域特定的指令模板，提高专业问题处理准确性

**实现机制：**

- 使用分层的系统提示（System Message）和用户提示（User Message）
- 系统提示定义了助手的角色、响应模式和输出格式要求
- 用户提示包含检索到的上下文信息和当前问题
- 采用结构化思维链引导模型进行意图分析和问题诊断
- 通过明确的指令要求模型使用特定格式输出思考过程和最终回复

### 3. 多轮对话功能
实现完整的多轮对话支持：

- 对话历史管理，保持上下文连贯性
- 智能上下文窗口管理，避免超出模型最大上下文长度
- 支持对话编辑和重新生成
- 对话状态持久化存储

**实现机制：**

- 使用 Django 模型 ConversationSession 存储对话历史
- 通过正则表达式解析和格式化对话历史
- 在每次请求中将历史对话作为上下文传递给模型
- 实现重新生成检测机制，避免重复对话条目
- 支持对话历史的持久化存储和检索

### 4. 改进的 RAG 架构
采用先进的 RAG 技术提升检索准确性：

- 混合检索策略（向量检索 + 关键词检索）
- 查询重写和扩展技术提升召回率
- 多阶段检索和重排序优化结果相关性
- 动态知识库更新机制

**实现机制：**

- 使用 LlamaIndex 和 ChromaDB 构建向量检索系统
- 实现混合检索策略，结合向量相似度和关键词匹配
- 通过查询重写映射表标准化用户输入
- 使用同义词库扩展查询关键词提升召回率
- 将检索结果按相关性分数排序并截取Top-K结果

### 5. 工作流与工具使用
系统集成工作流功能，支持模型调用外部工具：

- 定义可执行函数供模型调用
- 思维链（CoT）引导模型使用工具
- 工具执行结果反馈给模型形成闭环
- 支持自定义工具扩展系统能力 

**实现机制：**

- 通过 Prompt 指令引导模型使用特定工具（日志数据库、联网搜索）
- 在系统提示中明确定义可用工具及其使用场景
- 实现工具调用的条件判断和结果整合
- 通过思维链展示工具使用过程和结果分析

### 6. 联网搜索功能
系统支持实时联网搜索功能，能够在本地知识库无法提供足够信息时，从互联网获取最新的解决方案和相关信息：

- 集成 DuckDuckGo 搜索引擎
- 支持中英文搜索
- 实时获取最新技术资讯和解决方案
- 与本地知识库内容融合分析

**实现机制：**

- 使用 `ddgs` 库实现 DuckDuckGo 搜索功能
- 在后端服务中实现搜索结果的获取和格式化
- 将搜索结果作为上下文信息传递给大语言模型
- 通过 Prompt 指令引导模型合理使用联网搜索结果
- 支持搜索结果的相关性过滤和排序

### 7. HTML实时渲染

为了提升消息内容的可读性和交互性，系统实现了强大的HTML实时渲染功能：

- 支持 Markdown 格式实时渲染为 HTML，包括标题、段落、列表、代码块等
- 代码块语法高亮显示，支持多种编程语言
- 表格、链接、图片等富文本元素的正确渲染
- 支持在消息中嵌入并运行 HTML 和 JavaScript 代码片段

**实现机制：**

- 使用 `marked` 库将 Markdown 文本解析为 HTML
- 集成 `highlight.js` 实现代码块语法高亮
- 通过 `v-html` 指令将渲染后的 HTML 插入到 DOM 中
- 在消息组件更新后自动应用语法高亮和添加交互功能
- 为 HTML 和 JavaScript 代码块添加"运行"按钮，可在沙盒环境中预览效果
- 实现专业术语的悬停提示功能，提升用户体验

### 8. 智能查询优化

系统具备智能查询优化能力，能够自动识别和处理用户的输入，提高检索准确性：

- 查询重写：自动识别并纠正口语化表达、拼写错误和缩写
- 同义词扩展：通过同义词库扩展查询关键词，提升召回率
- 上下文感知：根据对话历史和用户意图优化查询语句

**实现机制：**

- 建立了包含常见口语化表达、拼写错误和缩写的标准映射表
- 构建了涵盖多个技术领域的同义词库
- 在查询处理过程中自动应用重写和扩展规则

### 9. 多模型管理与缓存

系统支持多种大语言模型的动态管理和高效调用：

- 动态模型加载：支持运行时切换不同大语言模型
- 模型缓存机制：避免重复加载模型，提高响应速度
- 统一模型接口：为不同模型提供一致的调用接口

支持以下大语言模型：

| 模型名       | 参数规模 | 特点                         |
|--------------|----------|------------------------------|
| DeepSeek-R1  | 7B       | 擅长逻辑推理和复杂分析       |
| Qwen3        | 8B       | 响应速度快，适合常规诊断     |
| Llama3       | 8B       | 通用性强，适应多类型问题     |

**实现机制：**

- 使用线程安全的锁机制管理模型缓存
- 实现模型名称解析和映射功能
- 通过 LlamaIndex 和 LangChain 集成多种模型和嵌入技术

### 10. 多格式文件上传与解析

系统支持多种常见文件格式的上传和内容解析，便于用户直接分析技术文档：

- 文本文件（.txt）：支持 UTF-8 和 GBK 编码
- Word 文档（.docx）：提取文档正文内容
- Excel 表格（.xlsx）：按工作表解析表格数据

**实现机制：**

- 前端通过文件选择器上传文件至后端
- 后端根据文件扩展名识别文件类型
- 使用 python-docx 库解析 Word 文档
- 使用 openpyxl 库解析 Excel 文件
- 将解析后的内容作为附件与用户消息一同发送
- 在聊天界面中显示附件名称，便于用户识别

## ⚙️ 技术架构

### 后端：Django

- `Django + Django Ninja`  
- 支持 SQLite / PostgreSQL 等数据库  
- RESTful API + Token 认证  
- 向量检索系统 + 联网搜索（DuckDuckGo）  

### 前端：Vue 3

- `Vue 3 + Composition API`  
- `Pinia` 状态管理  
- `Vue Router` 页面路由  
- 响应式设计 + 流式消息展示  
- Markdown 渲染支持  

---

## 📋 系统要求

### 后端
#### 向量数据库
- chromadb                  1.0.20
#### Django 框架
- django                    5.2.7
- django-cors-headers       4.9.0
- django-ninja              1.4.4 
#### LangChain 生态
- langchain                 0.3.27
- langchain-community       0.3.31
- langchain-core            0.3.76
- langchain-ollama          0.3.8
- langchain-openai          0.3.33
- langchain-text-splitters  0.3.11
#### LlamaIndex 生态
- llama-index               0.14.5
- llama-index-cli           0.5.3
- llama-index-core          0.14.5
- llama-index-embeddings-langchain 0.4.1
- llama-index-embeddings-openai    0.5.1
- llama-index-indices-managed-llama-cloud 0.9.4
- llama-index-instrumentation      0.4.2
- llama-index-llms-langchain       0.7.1
- llama-index-llms-openai          0.6.5
- llama-index-readers-file         0.5.4
- llama-index-readers-llama-parse  0.5.1
- llama-index-vector-stores-chroma 0.5.3
- llama-index-workflows            2.8.3
#### Ollama
- ollama                    0.6.0

### 前端
#### 运行时依赖
- axios: ^1.11.0
- highlight.js: ^11.11.1
- marked: ^16.4.1
- pinia: ^3.0.3
- vue: ^3.5.18
- vue-router: ^4.5.1
- vue-tabler-icons: ^2.21.0
#### 开发依赖
- @vitejs/plugin-vue: ^6.0.1
- vite: ^7.1.12

---

## 🚀 快速开始

### 1️⃣ 后端部署

```bash
# 克隆项目
git clone https://github.com/3145285451/llm.git

# 进入后端目录
cd django_backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
python manage.py runserver
```

---

### 2️⃣ 前端部署

```bash
# 进入前端目录
cd vue_frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

---

### 3️⃣ 模型准备

```bash
# 下载所需大模型
ollama pull deepseek-r1:7b
ollama pull qwen3:8b
ollama pull llama3:8b

# 下载向量嵌入模型
ollama pull bge-large:latest
```

---

## 🧪 使用说明

1. 访问前端界面：[http://localhost:8092]
2. 使用默认账号登录（用户名：任意，密码：`secret`）  
3. 输入技术问题或上传日志文件  
4. 系统将分析问题并提供解决方案  
5. 可在设置中切换模型或对话会话  

---

## 📡 API 接口

| 接口路径             | 方法   | 描述               |
|----------------------|--------|--------------------|
| `/api/login`         | POST   | 用户登录           |
| `/api/chat`          | POST   | 聊天接口（支持流式） |
| `/api/history`       | GET    | 获取会话历史       |
| `/api/history`       | DELETE | 清空会话历史       |
| `/api/glossary`      | GET    | 获取术语词典       |
| `/api/upload_file`   | POST   | 上传文件进行解析   |

---

## 📁 项目结构

```
.
.
├── django_backend                     # 后端项目
│   ├── deepseek_api                   # API 模块
│   │   ├── migrations                 # 数据库迁移文件
│   │   │   ├── 0001_initial.py
│   │   │   ├── 0002_alter_conversationsession_context.py
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── api.py                     # API 接口定义
│   │   ├── apps.py                    # Django应用配置
│   │   ├── models.py                  # 数据模型定义
│   │   ├── schemas.py                 # 数据结构定义
│   │   ├── services.py                # 业务逻辑处理
│   │   └── urls.py                    # API路由配置
│   ├── deepseek_project               # Django项目配置
│   │   ├── __init__.py
│   │   ├── asgi.py                    # ASGI配置
│   │   ├── settings.py                # 项目设置
│   │   ├── urls.py                    # 主路由配置
│   │   └── wsgi.py                    # WSGI配置
│   ├── manage.py                      # Django管理脚本
│   ├── topklogsystem.py               # 日志分析系统核心模块
│   └── requirements.txt               # Python依赖包列表
│
├── vue_frontend                       # 前端项目
│   ├── src
│   │   ├── assets                     # 静态资源
│   │   │   └── styles.css             # 全局样式文件
│   │   ├── components                 # Vue组件
│   │   │   ├── ChatInput.vue          # 聊天输入组件
│   │   │   ├── ChatMessage.vue        # 聊天消息组件
│   │   │   ├── HelloWorld.vue         # 示例组件
│   │   │   └── SessionList.vue        # 会话列表组件
│   │   ├── views                      # 页面视图
│   │   │   ├── Chat.vue               # 聊天页面
│   │   │   └── Login.vue              # 登录页面
│   │   ├── App.vue                    # 根组件
│   │   ├── api.js                     # API接口封装
│   │   ├── main.js                    # 入口文件
│   │   ├── router.js                  # 路由配置
│   │   └── store.js                   # 状态管理
│   ├── README.md                      # 前端说明文档
│   ├── index.html                     # HTML入口文件
│   ├── package-lock.json              # npm依赖锁定文件
│   ├── package.json                   # npm配置文件
│   └── vite.config.js                 # Vite配置文件
│
├── data                               # 知识库数据目录
│   └── log                            # 故障日志文件目录
│
├── vector_stores                      # 向量数据库目录
│
├── README.md                          # 项目主说明文档
├── code.md                            # 代码相关说明
└── 设计流程.md                        # 系统设计流程文档
```
