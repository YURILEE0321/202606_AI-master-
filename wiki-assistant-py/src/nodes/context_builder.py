from ..lib.logger import get_logger
from ..state import SourceRef, WikiAssistantState

logger = get_logger(__name__)


def context_builder(state: WikiAssistantState) -> dict:
    docs = state.get("reranked_docs", [])
    logger.info("CONTEXT_BUILDER_START docs=%d", len(docs))

    if not docs:
        logger.info("CONTEXT_BUILDER_RESULT docs=0 context_len=0 sources=0")
        logger.info("CONTEXT_BUILDER_END")
        return {"context": "", "sources": []}

    context = "\n\n".join(
        f"[{idx + 1}] ({doc['doc_id']} · {doc['title']} · {doc['section']})\n{doc['text']}"
        for idx, doc in enumerate(docs)
    )

    sources: list[SourceRef] = []
    seen = set()
    for doc in docs:
        if doc["doc_id"] in seen:
            continue
        seen.add(doc["doc_id"])
        sources.append(
            SourceRef(
                doc_id=doc["doc_id"],
                title=doc["title"],
                source_file=doc["source_file"],
                doc_type=doc["doc_type"],
            )
        )

    logger.info(
        "CONTEXT_BUILDER_RESULT context_len=%d sources=%s",
        len(context),
        [(s["doc_id"], s["title"]) for s in sources],
    )
    logger.info("CONTEXT_BUILDER_END")
    return {"context": context, "sources": sources}
