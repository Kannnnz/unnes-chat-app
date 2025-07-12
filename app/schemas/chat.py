from pydantic import BaseModel
from typing import List
from datetime import datetime

class ChatMessage(BaseModel):
    session_id: str
    message: str
    document_ids: List[str]

class ChatResponse(BaseModel):
    response: str
    
class ChatHistoryItem(BaseModel):
    sender: str
    content: str
    timestamp: datetime