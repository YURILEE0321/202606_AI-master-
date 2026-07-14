# 2026_aimaster_wikigen의 assistant 서비스가 쓰던 계약과 동일하게 맞춘 스키마.
# (assistant/app/schemas.py 참고) backend-proxy/frontend는 이 계약만 보고 우리 서비스를 호출한다.
from typing import List

from pydantic import BaseModel


class HistoryTurn(BaseModel):
    role: str
    text: str


class ProxyChatRequest(BaseModel):
    space_id: str
    question: str
    history: List[HistoryTurn] = []


class ProxySource(BaseModel):
    document_id: str
    title: str
    score: float


class ProxyChatResponse(BaseModel):
    answer: str
    sources: List[ProxySource] = []
