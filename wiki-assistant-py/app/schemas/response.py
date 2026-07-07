from typing import List, Optional

from pydantic import BaseModel


class ChatResponse(BaseModel):
    status: str  # "success" | "error"
    intent: Optional[str] = None
    keywords: Optional[List[str]] = None
    answer: Optional[str] = None
    confidence_score: Optional[float] = None
    retry_count: Optional[int] = None
    runtime: Optional[float] = None  # 초 단위
