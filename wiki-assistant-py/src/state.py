import operator
from typing import Annotated, List, Optional, TypedDict


class RetrievedChunk(TypedDict):
    id: str
    score: float
    text: str
    doc_id: str
    title: str
    doc_type: str
    category: str
    section: str
    tags: List[str]
    related_menus: List[str]
    source_file: str
    approval_status: str
    updated_date: str


class SourceRef(TypedDict):
    doc_id: str
    title: str
    source_file: str
    doc_type: str


class FinalAnswer(TypedDict):
    core_answer: str
    detail: str
    related_menus: List[str]
    references: List[str]


class WikiAssistantState(TypedDict, total=False):
    question: str
    # 최초 질문 원문. Query Rewriter가 question을 계속 고쳐 쓰므로, 답변 생성/로그 표시에는 이 값을 기준으로 삼는다.
    original_question: str
    intent: str
    keywords: List[str]
    search_query: str
    # Multi Query Retrieval(2차 retry)에서 생성되는 추가 검색 질의 변형들. 비어있으면 search_query 단일 검색.
    query_variants: List[str]
    retrieved_docs: List[RetrievedChunk]
    reranked_docs: List[RetrievedChunk]
    context: str
    sources: List[SourceRef]
    answer: Optional[FinalAnswer]
    confidence_score: float
    escalation_required: bool
    final_message: str
    # 재시도 루프 상태
    retry_count: int
    last_rewrite_technique: str
    attempt_log: Annotated[List[str], operator.add]
