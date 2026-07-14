# wiki/*.md(개별 문서 3건)를 읽어 청킹 -> 임베딩(LLM_PROVIDER에 따라 Gemini 또는 Azure OpenAI) -> Qdrant 적재,
# 문서 메타데이터는 Postgres에 upsert한다.
# 사용법: python -m scripts.ingest [--no-approve]
#   --no-approve : 적재 시 frontmatter의 approval_status(pending)를 그대로 저장한다.
#                  기본값은 데모 목적으로 approval_status를 "approved"로 강제 저장한다.
import sys
import uuid
from pathlib import Path

import frontmatter

from src.clients.llm import embed_texts
from src.clients.postgres import ensure_schema, upsert_document_metadata
from src.clients.qdrant import delete_by_doc_id, ensure_collection, upsert_chunks
from src.lib.chunk import chunk_markdown

_WIKI_DIR = Path(__file__).resolve().parent.parent / "wiki"
_EXCLUDED_FILES = {"_template.md", "AI-Wiki.md"}


def main() -> None:
    auto_approve = "--no-approve" not in sys.argv[1:]

    print("[ingest] Qdrant 컬렉션 확인/생성 중...")
    ensure_collection()
    print("[ingest] Postgres 테이블 확인/생성 중...")
    ensure_schema()

    files = sorted(
        p for p in _WIKI_DIR.glob("*.md") if p.name not in _EXCLUDED_FILES
    )
    if not files:
        raise RuntimeError(f"{_WIKI_DIR} 에서 적재할 문서를 찾지 못했습니다.")

    total_chunks = 0

    for path in files:
        post = frontmatter.load(path)
        data = post.metadata
        content = post.content

        doc_id = data.get("id")
        if not doc_id:
            print(f"[ingest] {path.name}: frontmatter에 id가 없어 건너뜁니다.")
            continue

        approval_status = "approved" if auto_approve else data.get("approval_status", "pending")
        chunks = chunk_markdown(content)

        print(f"[ingest] {path.name} ({doc_id}) -> {len(chunks)}개 청크, approval_status={approval_status}")

        vectors = embed_texts([c.text for c in chunks])

        delete_by_doc_id(doc_id)

        points = [
            {
                "id": str(uuid.uuid4()),
                "vector": vectors[idx],
                "payload": {
                    "docId": doc_id,
                    "title": data.get("title"),
                    "docType": data.get("doc_type"),
                    "category": data.get("category", ""),
                    "section": chunk.section,
                    "tags": data.get("tags", []),
                    "relatedMenus": data.get("related_menus", []),
                    "sourceFile": data.get("source_file", f"data/{path.name}"),
                    "approvalStatus": approval_status,
                    "updatedDate": data.get("updated_date", ""),
                    "text": chunk.text,
                },
            }
            for idx, chunk in enumerate(chunks)
        ]

        upsert_chunks(points)
        total_chunks += len(points)

        upsert_document_metadata(
            {
                "id": doc_id,
                "title": data.get("title"),
                "doc_type": data.get("doc_type"),
                "category": data.get("category", ""),
                "version": data.get("version", ""),
                "created_date": data.get("created_date") or None,
                "updated_date": data.get("updated_date") or None,
                "approval_status": approval_status,
                "tags": data.get("tags", []),
                "source_file": data.get("source_file", f"data/{path.name}"),
                "related_menus": data.get("related_menus", []),
                "summary": data.get("summary", ""),
            }
        )

    print(f"[ingest] 완료: 문서 {len(files)}건, 청크 {total_chunks}건 적재")


if __name__ == "__main__":
    main()
