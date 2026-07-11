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
    # 질문에 명시적으로 언급된 구체적 개체명(메뉴명/용어/시스템명/설비명/코드 등 고유명사). keywords보다 좁고 정확한 앵커.
    entities: List[str]
    keywords: List[str]
    search_query: str
    # Multi Query Retrieval(2차 retry)에서 생성되는 추가 검색 질의 변형들. 비어있으면 search_query 단일 검색.
    query_variants: List[str]
    retrieved_docs: List[RetrievedChunk]
    reranked_docs: List[RetrievedChunk]
    context: str
    sources: List[SourceRef]
    answer: Optional[FinalAnswer]
    # Confidence Checker 세부 지표 (Similarity + RAGAS 사전 지표의 가중 평균 = confidence_score)
    similarity_score: float
    context_precision: float
    context_recall: float
    ragas_score: float  # (context_precision + context_recall) / 2, 답변 생성 전 계산 가능한 사전 지표
    confidence_score: float  # Final Score = similarity_score*0.4 + ragas_score*0.6
    escalation_required: bool
    final_message: str
    # 답변 생성 후에만 계산 가능한 사후 지표(재시도 트리거에는 쓰지 않음, 참고/로깅 전용)
    faithfulness: float
    answer_relevancy: float
    ragas_full_score: float  # 4개 지표 25%씩 반영한 전체 RAGAS 점수(참고용)
    # 재시도 루프 상태
    retry_count: int
    last_rewrite_technique: str
    attempt_log: Annotated[List[str], operator.add]
