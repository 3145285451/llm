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

    def generate_response(
        self, query: str, context: Dict, history: List[Dict] = None
    ) -> str:
        prompt_messages = self._build_prompt(query, context, history)
        try:
            response_message = self.llm.invoke(prompt_messages)
            return response_message
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return f"生成响应时出错: {str(e)}"

    def _build_prompt(
        self, query: str, context: Dict, history: List[Dict] = None
    ) -> List:
        system_message = SystemMessagePromptTemplate.from_template(
            "你是一个智能日志分析助手。"
            "你的回答应该清晰、专业，并使用 Markdown 格式进行排版（例如使用列表、代码块、粗体、表格等）以提高可读性。"
        )

        log_context = "## 相关历史日志参考:\n"
        if not context:
            log_context += "（未检索到相关历史日志）\n"
        else:
            for i, log in enumerate(context, 1):
                log_context += f"日志 {i} : {log['content']}\n"

        # (*** 修复点 ***)
        # 修改 HumanMessagePromptTemplate，赋予 LLM 路由能力
        user_message_template = HumanMessagePromptTemplate.from_template(
            """
            {log_context}
            ---
            ## 当前需要分析的问题:
            {query}

            ---
            ## 你的任务:
            请仔细阅读“当前需要分析的问题”和完整的“对话历史”（在 `chat_history` 中）。

            1.  **优先判断意图**：
                * 如果“当前需要分析的问题”是关于**对话历史**的提问（例如：“我之前问了什么”、“总结一下”、“你刚才说了什么”），
                    请你**必须优先并只使用 `chat_history`** 来回答，**忽略**“相关历史日志参考”。
                * 如果“当前需要分析的问题”是一个**新的日志分析请求**（例如：“数据库连接失败”、“查询超时”），
                    请你**优先使用“相关历史日志参考”** 来提供一个详细的分析报告。

            2.  **生成回答**：
                * 根据你的判断，生成一个直接、清晰的回答。
                * 如果问题是关于历史的，请直接从历史中总结答案。
                * 如果问题是关于日志的，请按分析报告的格式回答。
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
                    formatted_history.append(AIMessage(content=msg["content"]))

        return prompt_template.format_prompt(
            chat_history=formatted_history, log_context=log_context, query=query
        ).to_messages()

    def query(self, query: str, history: List[Dict] = None) -> Dict:
        # RAG (检索) 仍然总是运行，但这没关系
        log_results = self.retrieve_logs(query)

        # LLM (生成) 会根据我们新的 Prompt 来决定是否使用 log_results
        response = self.generate_response(query, log_results, history)

        return {"response": response, "retrieval_stats": len(log_results)}


if __name__ == "__main__":
    system = TopKLogSystem(
        log_path="./data/log", llm="deepseek-r1:7b", embedding_model="bge-large:latest"
    )

    query1 = "我遇到了数据库问题"
    result1 = system.query(query1)
    print("查询1:", query1)
    print("响应1:", result1["response"])

    history_example = [
        {"role": "user", "content": query1},
        {"role": "assistant", "content": result1["response"]},
    ]

    query2 = "是连接池耗尽的问题，如何解决？"
    result2 = system.query(query2, history=history_example)
    print("\n查询2 (带历史):", query2)
    print("响应2:", result2["response"])
