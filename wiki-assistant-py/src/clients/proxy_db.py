# 2026_aimaster_wikigen/assistant의 조회 로직을 그대로 재사용한다:
# - get_allowed_documents: assistant/app/routers/chat.py::_allowed_documents와 동일한 쿼리
# - get_wikimd_bodies: assistant/app/graph/nodes.py::build_context가 WikiMd를 읽는 방식과 동일
# 완전히 별개의 커넥션/스키마이며, 여기서는 절대 쓰기(INSERT/UPDATE/DDL)를 하지 않는다.
from typing import Dict, List

from .proxy_models import Document, ProxySessionLocal, WikiMd


def _require_session():
    if ProxySessionLocal is None:
        raise RuntimeError(
            "PROXY_DATABASE_URL이 설정되지 않았습니다. backend-proxy의 Postgres(documents/wikimd) 연결 문자열이 필요합니다."
        )
    return ProxySessionLocal()


def get_allowed_documents(space_id: str) -> Dict[str, dict]:
    """space_id 내 승인된 문서의 wiki_doc_id -> {document_id, title} 매핑을 반환한다."""
    db = _require_session()
    try:
        rows = (
            db.query(Document.document_id, Document.wiki_doc_id, Document.title)
            .filter(
                Document.space_id == space_id,
                Document.status == "approved",
                Document.wiki_doc_id.isnot(None),
            )
            .all()
        )
    finally:
        db.close()

    return {row.wiki_doc_id: {"document_id": row.document_id, "title": row.title} for row in rows}


def get_wikimd_bodies(doc_ids: List[str]) -> Dict[str, dict]:
    """wiki_doc_id 목록에 대한 {title, body, doc_type}을 wikimd에서 조회한다."""
    if not doc_ids:
        return {}

    db = _require_session()
    try:
        rows = db.query(WikiMd).filter(WikiMd.doc_id.in_(doc_ids)).all()
    finally:
        db.close()

    return {row.doc_id: {"title": row.title, "body": row.body, "doc_type": row.doc_type or ""} for row in rows}
