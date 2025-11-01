import os

# chroma 不上传数据
os.environ["ANONYMIZED_TELEMETRY"] = "false"
os.environ["DISABLE_TELEMETRY"] = "1"
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"

import json
import logging
import pandas as pd
from typing import Any, Dict, List

# langchain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)
from langchain_ollama import OllamaLLM, OllamaEmbeddings

# llama-index & chroma
import chromadb
from llama_index.core import Settings  # 全局
from llama_index.core import Document
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore

# 日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# (新增) 导入 re
import re


class TopKLogSystem:
    def __init__(
        self,
        log_path: str,
        llm: str,
        embedding_model: str,
    ) -> None:
        self.embedding_model = OllamaEmbeddings(model=embedding_model)
        self.llm = OllamaLLM(model=llm, temperature=0.1)

        Settings.llm = self.llm
        Settings.embed_model = self.embedding_model

        self.log_path = log_path
        self.log_index = None
        self.vector_store = None
        self._build_vectorstore()

    def _build_vectorstore(self):
        vector_store_path = "./data/vector_stores"
        os.makedirs(vector_store_path, exist_ok=True)

        chroma_client = chromadb.PersistentClient(path=vector_store_path)
        log_collection = chroma_client.get_or_create_collection("log_collection")

        log_vector_store = ChromaVectorStore(chroma_collection=log_collection)
        log_storage_context = StorageContext.from_defaults(
            vector_store=log_vector_store
        )
        if log_documents := self._load_documents(self.log_path):
            self.log_index = VectorStoreIndex.from_documents(
                log_documents,
                storage_context=log_storage_context,
                show_progress=True,
            )
            logger.info(f"日志库索引构建完成，共 {len(log_documents)} 条日志")

    @staticmethod
    def _load_documents(data_path: str) -> List[Document]:
        if not os.path.exists(data_path):
            logger.warning(f"数据路径不存在: {data_path}")
            return []
        documents = []
        for file in os.listdir(data_path):
            ext = os.path.splitext(file)[1]
            if ext not in [".txt", ".md", ".json", ".jsonl", ".csv"]:
                continue
            file_path = f"{data_path}/{file}"
            try:
                if ext == ".csv":
                    chunk_size = 1000
                    for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                        for row in chunk.itertuples(index=False):
                            content = str(row).replace("Pandas", " ")
                            documents.append(Document(text=content))
                else:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        doc = Document(
                            text=content,
                        )
                        documents.append(doc)
            except Exception as e:
                logger.error(f"加载文档失败 {file_path}: {e}")
        return documents

    def retrieve_logs(self, query: str, top_k: int = 10) -> List[Dict]:
        if not self.log_index:
            return []
        try:
            retriever = self.log_index.as_retriever(similarity_top_k=top_k)
            results = retriever.retrieve(query)
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {"content": result.text, "score": result.score}
                )
            return formatted_results
        except Exception as e:
            logger.error(f"日志检索失败: {e}")
            return []

    # (修改) generate_response 改为流式生成器
    def generate_response(
        self, query: str, context: Dict, history: List[Dict] = None
    ):  # -> Generator[str, None, None]:
        prompt_messages = self._build_prompt(query, context, history)
        try:
            # (修改) 使用 stream 并 yield 原始块
            for chunk in self.llm.stream(prompt_messages):
                yield chunk

        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            yield f"生成响应时出错: {str(e)}"  # 作为单个错误块返回

    def _build_prompt(
        self, query: str, context: Dict, history: List[Dict] = None
    ) -> List:

        # 1. (*** 修复 ***) 强化 System 角色
        system_message = SystemMessagePromptTemplate.from_template(
            """
            你是一个多任务SRE助手。你的首要任务是 **[判断意图]**，然后根据意图选择正确的 **[响应模式]**。

            你有两种响应模式：
            1.  **[SRE分析模式]**: 当用户的问题与故障排查、日志分析、系统错误相关时使用。
            2.  **[常规对话模式]**: 当用户进行常规闲聊 (如 "你好")、历史回顾 (如 "我刚才问了什么") 或提出与日志无关的问题 (如 "介绍一下天津大学") 时使用。

            你的回答必须遵循以下质量要求：
            1.  **专业严谨**：在 [SRE分析模式] 下，你的分析必须基于上下文（日志或历史），严禁凭空猜测。
            2.  **清晰可读**：使用 Markdown 格式（如列表、代码块、粗体）来组织你的回答。
            
            **[!!! 绝对指令 !!!]**
            你 **必须** 使用 `<thought>...</thought>` 标签来包裹你的所有内部思考步骤。
            你的最终回复 (面向用户) **绝不能** 包含 `<thought>` 标签或 "步骤 1", "步骤 2" 等分析字样。
            用户 **永远** 不应该看到 `<thought>` 和 `</thought>` 标签。
            """
        )

        # 2. 准备日志上下文
        log_context_str = "## [可用工具 (SRE模式专用)] 相关日志参考:\n"
        if not context:
            log_context_str += "（未检索到相关历史日志，仅在SRE模式下报告此信息）\n"
        else:
            for i, log in enumerate(context, 1):
                log_context_str += f"日志 {i} : {log['content']}\n"

        # 3. (*** 修复 ***) 强化 User 模板的结构
        user_message_template = HumanMessagePromptTemplate.from_template(
            """
            ## [可用工具 (SRE模式专用)]
            {log_context}
            
            ---
            ## [任务] 当前用户问题:
            {query}
            ---

            ## [执行指令]
            请严格按照以下步骤在 <thought> 块中进行内部思考，然后生成最终答复。

            <thought>
            **步骤 1: 意图分析 (Intent Analysis)**
            * 用户当前问题是："{query}"
            * 结合聊天历史，分析用户的意图。
            * 意图判断：(填写 [SRE分析模式] 或 [常规对话模式])

            **步骤 2: 响应策略 (Response Strategy)**
            * **如果 (If) 意图是 [常规对话模式]**:
                * 我将生成一个友好、对应的回复，忽略 [可用工具] 中的日志。
            * **如果 (If) 意图是 [SRE分析模式]**:
                * 我必须使用下面的 [SRE分析框架] 来分析 [可用工具] 中的日志，并结合用户问题进行回答。

            **步骤 3: SRE分析框架 (仅SRE模式执行)**
            * **a. 问题现象 (Symptom):**
                * (总结用户 {query} 中描述的核心问题。)
            * **b. 日志关联 (Log Correlation):**
                * (审查 [可用工具] 中的日志。哪些日志条目与 [Symptom] 相关？如果日志不相关或缺失，在此处注明。)
            * **c. 根本原因 (Root Cause Hypothesis):**
                * (基于 [Log Correlation] 和 {query}，提出1-2个最可能的根本原因。如果信息不足，则指出需要哪些额外信息。)
            * **d. 建议方案 (Actionable Steps):**
                * (提出具体的解决步骤或进一步的排查指令。)

            **步骤 4: 最终回复 (Draft Final Response)**
            * (基于 [步骤2] 或 [步骤3] 的分析，在此处草拟给用户的最终回复。确保使用 Markdown 格式，并且不包含任何 <thought> 标签或分析步骤字样。)
            </thought>

            [此处开始是给用户的最终回复]
            """
        )

        prompt_template = ChatPromptTemplate.from_messages(
            [
                system_message,
                MessagesPlaceholder(variable_name="chat_history"),
                user_message_template,
            ]
        )

        formatted_history = []
        if history:
            for msg in history:
                if msg["role"] == "user":
                    formatted_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    # (*** 关键修复 ***)
                    # 确保传入历史的 AI 回复也是清理过的，避免污染上下文
                    clean_content = re.sub(
                        r"<ctrl3347>.*?<ctrl3348>\s*",
                        "",
                        msg["content"],
                        flags=re.DOTALL,
                    )
                    formatted_history.append(AIMessage(content=clean_content.strip()))
                else:
                    # 容错
                    formatted_history.append(AIMessage(content=msg["content"]))

        return prompt_template.format_prompt(
            chat_history=formatted_history,
            log_context=log_context_str,
            query=query,
        ).to_messages()

    def query(
        self, query: str, history: List[Dict] = None
    ):  # -> Generator[str, None, None]:
        # RAG (检索) 仍然总是运行
        log_results = self.retrieve_logs(query)

        # LLM (生成)
        # (修改) 迭代 generate_response 并 yield 原始文本块
        for chunk in self.generate_response(query, log_results, history):
            yield chunk  # yield 原始 str 块


# (修改) if __name__ == "__main__" 部分需要修改，因为它现在是流
if __name__ == "__main__":
    system = TopKLogSystem(
        log_path="./data/log", llm="deepseek-r1:7b", embedding_model="bge-large:latest"
    )

    query1 = "我遇到了数据库问题"
    print("查询1:", query1)
    print("响应1 (流式):")
    full_response_1 = ""
    for chunk in system.query(query1):  # (修改) 迭代
        print(chunk, end="", flush=True)  # (修改) 实时打印
        full_response_1 += chunk
    print("\n--- 流结束 ---")

    history_example = [
        {"role": "user", "content": query1},
        {"role": "assistant", "content": full_response_1},  # (修改) 使用累积的回复
    ]

    # (*** 测试意图区分 B ***)
    query2 = "我刚才问了什么？"
    print("\n查询2 (测试历史对话):", query2)
    print("响应2 (流式):")
    full_response_2 = ""
    for chunk in system.query(query2, history=history_example):  # (修改) 迭代
        print(chunk, end="", flush=True)
        full_response_2 += chunk
    print("\n--- 流结束 ---")

    # (*** 测试意图区分 A ***)
    query3 = "是连接池耗尽的问题，如何解决？"
    history_example.append({"role": "user", "content": query2})
    history_example.append({"role": "assistant", "content": full_response_2})
    result3 = system.query(query3, history=history_example)
    print("\n查询3 (测试日志分析):", query3)
    print("响应3 (流式):")
    full_response_3 = ""
    for chunk in system.query(query3, history=example_history):  # (修改) 迭代
        print(chunk, end="", flush=True)
        full_response_3 += chunk
    print("\n--- 流结束 ---")

    # (*** 测试意图区分 C ***)
    query4 = "你好"
    history_example.append({"role": "user", "content": query3})
    history_example.append({"role": "assistant", "content": full_response_3})
    result4 = system.query(query4, history=history_example)
    print("\n查询4 (测试常规对话):", query4)
    print("响应4 (流式):")
    for chunk in system.query(query4, history=history_example):  # (修改) 迭代
        print(chunk, end="", flush=True)
    print("\n--- 流结束 ---")
