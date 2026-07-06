from ..state import SourceRef, WikiAssistantState


def context_builder(state: WikiAssistantState) -> dict:
    docs = state.get("reranked_docs", [])

    if not docs:
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

    return {"context": context, "sources": sources}
