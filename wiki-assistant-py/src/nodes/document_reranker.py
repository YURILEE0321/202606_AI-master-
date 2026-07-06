from datetime import datetime
from typing import List

from ..config import config
from ..state import RetrievedChunk, WikiAssistantState


def _keyword_overlap_score(text: str, keywords: List[str]) -> float:
    if not keywords:
        return 0.0
    lower_text = text.lower()
    hits = sum(1 for k in keywords if k.lower() in lower_text)
    return hits / len(keywords)


def _parse_date(value: str):
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _recency_score(updated_date: str, all_dates: List[str]) -> float:
    if not updated_date:
        return 0.0
    times = [t for t in (_parse_date(d) for d in all_dates if d) if t is not None]
    if not times:
        return 0.0
    min_t, max_t = min(times), max(times)
    if max_t == min_t:
        return 1.0
    t = _parse_date(updated_date)
    if t is None:
        return 0.0
    return (t - min_t) / (max_t - min_t)


# vector 유사도 70%, 키워드 일치 15%, 최신성 10%로 재정렬한다.
def document_reranker(state: WikiAssistantState) -> dict:
    docs = state.get("retrieved_docs", [])
    all_dates = [d["updated_date"] for d in docs]
    keywords = state.get("keywords", [])

    scored = []
    for doc in docs:
        kw = _keyword_overlap_score(doc["text"], keywords)
        rec = _recency_score(doc["updated_date"], all_dates)
        combined = 0.75 * doc["score"] + 0.15 * kw + 0.1 * rec
        scored.append((doc, combined))

    scored.sort(key=lambda pair: pair[1], reverse=True)

    reranked_docs: List[RetrievedChunk] = [
        {**doc, "score": combined} for doc, combined in scored[: config.rerank_top_n]
    ]

    return {"reranked_docs": reranked_docs}
