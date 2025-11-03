from ninja import Schema
from typing import Optional, List, Dict


class LoginIn(Schema):
    username: str
    password: str


class LoginOut(Schema):
    api_key: str
    expiry: int


class ChatIn(Schema):
    session_id: str = "default_session"
    user_input: str
    context: Optional[List[Dict[str, str]]] = None  
    use_db_search: bool = True  # (新增) 默认开启数据库
    use_web_search: bool = False # (新增) 默认关闭联网


class ChatOut(Schema):
    content: str  # 最终回复
    think_process: Optional[str] = None  # 思考过程
    duration: Optional[float] = None  # 耗时


class HistoryOut(Schema):
    history: str


class ErrorResponse(Schema):
    error: str
