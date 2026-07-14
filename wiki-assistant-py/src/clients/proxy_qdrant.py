# 2026_aimaster_wikigen/assistant의 app/clients/vectordb.py 검색 로직을 그대로 재사용한다.
# 같은 Qdrant 클러스터(clients/qdrant.py의 client 인스턴스 재사용)이지만 우리 자체 컬렉션
# (ai_wiki_chunks)과는 이름/payload 스키마가 다르다. 여기서는 절대 upsert/delete/create_collection
# 등 쓰기 작업을 하지 않는다(남의 컬렉션이므로 읽기 전용).
from typing import List

from qdrant_client.models import FieldCondition, Filter, MatchAny

from ..config import config
from .qdrant import client


def _doc_id_filter(allowed_doc_ids: List[str]) -> Filter:
    return Filter(must=[FieldCondition(key="doc_id", match=MatchAny(any=allowed_doc_ids))])


def search_summary(query_vector: List[float], allowed_doc_ids: List[str], top_k: int) -> List[dict]:
    hits = client.query_points(
        collection_name=config.proxy_qdrant_summary_collection,
        query=query_vector,
        query_filter=_doc_id_filter(allowed_doc_ids),
        limit=top_k,
    ).points
    return [{"doc_id": h.payload["doc_id"], "title": h.payload.get("title", ""), "score": h.score} for h in hits]


def search_chunk(query_vector: List[float], allowed_doc_ids: List[str], top_k: int) -> List[dict]:
    hits = client.query_points(
        collection_name=config.proxy_qdrant_chunk_collection,
        query=query_vector,
        query_filter=_doc_id_filter(allowed_doc_ids),
        limit=top_k,
    ).points
    return [
        {"doc_id": h.payload["doc_id"], "section_path": h.payload.get("section_path", ""), "score": h.score}
        for h in hits
    ]
