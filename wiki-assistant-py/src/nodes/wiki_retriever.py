from typing import Any, Dict

from ..clients.llm import embed_text
from ..clients.qdrant import search_chunks
from ..config import config
from ..state import RetrievedChunk, WikiAssistantState

# 승인된 Wiki만 답변 근거로 사용한다 (시스템 프롬프트 원칙).
_ALLOWED_APPROVAL_STATUSES = ["approved"]


def _to_retrieved_chunk(id_: str, score: float, payload: Dict[str, Any]) -> RetrievedChunk:
    return RetrievedChunk(
        id=id_,
        score=score,
        text=str(payload.get("text", "")),
        doc_id=str(payload.get("docId", "")),
        title=str(payload.get("title", "")),
        doc_type=str(payload.get("docType", "")),
        category=str(payload.get("category", "")),
        section=str(payload.get("section", "")),
        tags=list(payload.get("tags") or []),
        related_menus=list(payload.get("relatedMenus") or []),
        source_file=str(payload.get("sourceFile", "")),
        approval_status=str(payload.get("approvalStatus", "")),
        updated_date=str(payload.get("updatedDate", "")),
    )


# Multi Query Retrieval(2차 retry) 시 query_variants에 여러 질의가 담긴다.
# 각 질의로 개별 검색을 수행한 뒤, 동일 청크(id)는 가장 높은 점수만 남기고 합친다.
def wiki_retriever(state: WikiAssistantState) -> dict:
    primary_query = state.get("search_query") or state["question"]
    variants = [q for q in state.get("query_variants", []) if q and q != primary_query]
    queries = [primary_query, *variants]

    merged: Dict[str, Dict[str, Any]] = {}
    for query in queries:
        vector = embed_text(query)
        results = search_chunks(vector, config.top_k, _ALLOWED_APPROVAL_STATUSES)
        for r in results:
            point_id = str(r.id)
            payload = r.payload or {}
            existing = merged.get(point_id)
            if not existing or r.score > existing["score"]:
                merged[point_id] = {"score": r.score, "payload": payload}

    retrieved_docs = [
        _to_retrieved_chunk(point_id, entry["score"], entry["payload"]) for point_id, entry in merged.items()
    ]
    retrieved_docs.sort(key=lambda d: d["score"], reverse=True)

    return {"retrieved_docs": retrieved_docs}
