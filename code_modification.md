### 1.对文件加载函数进行了修改,添加了可加载的文件的种类

```
#(修改)该函数用来读取文档,添加可读取文档类型
    @staticmethod
    def _load_documents(data_path: str) -> List[Document]:
        if not os.path.exists(data_path):
            logger.warning(f"数据路径不存在: {data_path}")
            return []
        documents = []
        for file in os.listdir(data_path):
            ext = os.path.splitext(file)[1]
            if ext not in [".txt", ".md", ".json", ".jsonl", ".csv", ".log", ".xml", ".yaml", ".yml", ".docx", ".pdf"]:
                continue
            file_path = f"{data_path}/{file}"
            try:
                if ext == ".csv":
                    documents.extend(TopKLogSystem._process_csv(file_path))
                elif ext in [".json", ".jsonl"]:
                    documents.extend(TopKLogSystem._process_json(file_path, ext))
                elif ext in [".yaml", ".yml"]:
                    documents.extend(TopKLogSystem._process_yaml(file_path))
                elif ext == ".xml":
                    documents.extend(TopKLogSystem._process_xml(file_path))
                elif ext == ".log":
                    documents.extend(TopKLogSystem._process_log(file_path))
                elif ext == ".docx":
                    documents.extend(TopKLogSystem._process_docx(file_path))
                elif ext == ".pdf":
                    documents.extend(TopKLogSystem._process_pdf(file_path))
                else:
                    documents.extend(TopKLogSystem._process_text(file_path))
            except Exception as e:
                logger.error(f"加载文档失败 {file_path}: {e}")
        return documents

    #(添加)各种文件类型的处理函数
    @staticmethod
    def _process_csv(file_path: str) -> List[Document]:
        documents = []
        chunk_size = 1000
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            for row in chunk.itertuples(index=False):
                content = str(row).replace("Pandas", " ")
                documents.append(Document(text=content))
        return documents

    @staticmethod
    def _process_json(file_path: str, ext: str) -> List[Document]:
        documents = []
        with open(file_path, "r", encoding="utf-8") as f:
            if ext == ".json":
                data = json.load(f)
                documents.append(Document(text=json.dumps(data, ensure_ascii=False)))
            elif ext == ".jsonl":
                for line in f:
                    data = json.loads(line.strip())
                    documents.append(Document(text=json.dumps(data, ensure_ascii=False)))
        return documents

    @staticmethod
    def _process_yaml(file_path: str) -> List[Document]:
        documents = []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append(Document(text=content))
        return documents

    @staticmethod
    def _process_xml(file_path: str) -> List[Document]:
        documents = []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append(Document(text=content))
        return documents

    @staticmethod
    def _process_log(file_path: str) -> List[Document]:
        documents = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                documents.append(Document(text=line.strip()))
        return documents

    @staticmethod
    def _process_docx(file_path: str) -> List[Document]:
        documents = []
        doc = DocxDocument(file_path)
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                documents.append(Document(text=paragraph.text.strip()))
        return documents

    @staticmethod
    def _process_pdf(file_path: str) -> List[Document]:
        documents = []
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                documents.append(Document(text=text.strip()))
        return documents

    @staticmethod
    def _process_text(file_path: str) -> List[Document]:
        documents = []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            documents.append(Document(text=content))
        return documents
```
