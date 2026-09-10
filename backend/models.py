from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
    customer_email: Optional[str] = None


class ToolCallLog(BaseModel):
    tool_name: str
    tool_input: dict


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    escalated: bool = False
    tool_calls: List[ToolCallLog] = []


class ResetRequest(BaseModel):
    session_id: str
