from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatMessageItem(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text content")

class ChatRequest(BaseModel):
    user_id: Optional[int] = Field(None, description="Active user ID for tailored contextual response")
    message: str = Field(..., min_length=1, max_length=2000, description="User's query or instruction")
    history: Optional[List[ChatMessageItem]] = Field(default=[], description="Recent conversation turns")

class ChatActionSchema(BaseModel):
    type: str
    label: str
    feedback: Optional[str] = None
    url: Optional[str] = None

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI response text")
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    plan_version: Optional[int] = None
    suggested_action: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M"))

class ChatHistoryItem(BaseModel):
    id: int
    role: str
    message: str
    created_at: str

    class Config:
        from_attributes = True
