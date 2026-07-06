from ..state import WikiAssistantState


# Question Analyzer가 추출한 intent/keywords를 바탕으로 Retriever가 임베딩할 검색 질의를 구성한다.
# 매 루프(재시도 포함)마다 실행되며, 별도 LLM 호출 없이 결정론적으로 조합한다
# (Query Rewriter가 이미 question 자체를 개선해 넘겨주므로 여기서는 keywords 가중 결합만 수행).
def query_optimizer(state: WikiAssistantState) -> dict:
    keyword_part = " ".join(state.get("keywords", []))
    search_query = " ".join(part for part in [keyword_part, state["question"]] if part).strip()

    return {"search_query": search_query}
