from typing import Any, Dict, List, Optional, Sequence

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from ..config import config

client = QdrantClient(url=config.qdrant_url, api_key=config.qdrant_api_key)

# gemini-embedding-001과 text-embedding-3-large 모두 기본 출력 차원이 3072라 프로바이더 전환 시에도 그대로 쓴다.
_VECTOR_SIZE = 3072


def ensure_collection() -> None:
    if not client.collection_exists(config.qdrant_collection):
        client.create_collection(
            collection_name=config.qdrant_collection,
            vectors_config=qmodels.VectorParams(size=_VECTOR_SIZE, distance=qmodels.Distance.COSINE),
        )
    # docId(삭제/재적재 시 필터), approvalStatus(검색 시 필터)는 인덱싱된 payload 필드여야 filter 사용이 가능하다.
    # payload 키는 TypeScript 버전이 이미 적재한 데이터와 호환되도록 camelCase를 그대로 사용한다.
    client.create_payload_index(config.qdrant_collection, field_name="docId", field_schema="keyword")
    client.create_payload_index(config.qdrant_collection, field_name="approvalStatus", field_schema="keyword")


def delete_by_doc_id(doc_id: str) -> None:
    client.delete(
        collection_name=config.qdrant_collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(must=[qmodels.FieldCondition(key="docId", match=qmodels.MatchValue(value=doc_id))])
        ),
    )


def upsert_chunks(points: List[Dict[str, Any]]) -> None:
    if not points:
        return
    client.upsert(
        collection_name=config.qdrant_collection,
        points=[qmodels.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"]) for p in points],
    )


def search_chunks(
    vector: Sequence[float],
    limit: int,
    approval_statuses: List[str],
    doc_ids: Optional[List[str]] = None,
):
    # doc_ids가 주어지면(예: backend-proxy의 space_id로 걸러진 승인 문서 목록) approvalStatus와 AND로 묶어
    # 그 문서들만 검색 대상으로 좁힌다. docId에는 ensure_collection()에서 이미 keyword 인덱스를 만들어뒀다.
    must: List[qmodels.FieldCondition] = [
        qmodels.FieldCondition(key="approvalStatus", match=qmodels.MatchAny(any=approval_statuses))
    ]
    if doc_ids:
        must.append(qmodels.FieldCondition(key="docId", match=qmodels.MatchAny(any=doc_ids)))

    return client.query_points(
        collection_name=config.qdrant_collection,
        query=list(vector),
        limit=limit,
        with_payload=True,
        query_filter=qmodels.Filter(must=must),
    ).points
