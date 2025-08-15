from pydantic import BaseModel
from typing import List, Dict, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatResponse(BaseModel):
    user_transcript: Optional[str]
    llm_text: Optional[str]
    audio_url: Optional[str]
    history: List[Dict[str, str]]

class ErrorResponse(BaseModel):
    error: str
    audio_url: Optional[str] = None
