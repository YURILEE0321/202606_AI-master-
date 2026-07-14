from typing import Any, Dict

from ..clients import proxy_db, proxy_embeddings, proxy_qdrant
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


def _own_retrieve(state: WikiAssistantState) -> dict:
    """우리 자체 Qdrant 컬렉션(ai_wiki_chunks)에서 검색한다 (CLI/기존 /api/v1/chat 경로)."""
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


def _proxy_retrieve(state: WikiAssistantState) -> dict:
    """2026_aimaster_wikigen의 실제 Qdrant(wiki_summary/wiki_chunk)에서 검색한다
    (/assistant/v1/chat 경로, state["space_id"]가 있을 때만 진입).

    wiki_chunk/wiki_summary의 payload에는 본문 텍스트가 없어(메타데이터만 있음), doc_id 단위로
    최고 점수만 남긴 뒤 실제 본문은 wikidb.wikimd(Postgres)에서 한 번에 가져온다. 그 결과를
    RetrievedChunk로 변환하면 이후 노드(Reranker/Confidence Checker/Answer Generator)는
    데이터 출처를 몰라도 동일하게 동작한다.
    """
    primary_query = state.get("search_query") or state["question"]
    variants = [q for q in state.get("query_variants", []) if q and q != primary_query]
    queries = [primary_query, *variants]
    allowed_doc_ids = state.get("allowed_doc_ids", [])

    if not allowed_doc_ids:
        return {"retrieved_docs": []}

    doc_scores: Dict[str, float] = {}
    for query in queries:
        vector = proxy_embeddings.embed_text_aitl(query)
        hits = proxy_qdrant.search_summary(vector, allowed_doc_ids, config.proxy_top_k_summary) + proxy_qdrant.search_chunk(
            vector, allowed_doc_ids, config.proxy_top_k_chunk
        )
        for hit in hits:
            doc_id = hit["doc_id"]
            doc_scores[doc_id] = max(doc_scores.get(doc_id, 0.0), hit["score"])

    if not doc_scores:
        return {"retrieved_docs": []}

    bodies = proxy_db.get_wikimd_bodies(list(doc_scores.keys()))
    doc_id_map = state.get("doc_id_map", {})

    retrieved_docs = []
    for doc_id, score in doc_scores.items():
        body_info = bodies.get(doc_id)
        if not body_info:
            continue
        retrieved_docs.append(
            RetrievedChunk(
                id=doc_id,
                score=score,
                text=body_info["body"],
                doc_id=doc_id,
                title=body_info["title"],
                doc_type=body_info.get("doc_type") or "",
                category="",
                section="",
                tags=[],
                related_menus=[],
                source_file=f"wikidb:{doc_id_map.get(doc_id, {}).get('document_id', doc_id)}",
                approval_status="approved",
                updated_date="",
            )
        )
    retrieved_docs.sort(key=lambda d: d["score"], reverse=True)
    return {"retrieved_docs": retrieved_docs}


# Multi Query Retrieval(3차 retry) 시 query_variants에 여러 질의가 담긴다.
# 각 질의로 개별 검색을 수행한 뒤, 동일 청크(id)는 가장 높은 점수만 남기고 합친다.
def wiki_retriever(state: WikiAssistantState) -> dict:
    if state.get("space_id"):
        return _proxy_retrieve(state)
    return _own_retrieve(state)
