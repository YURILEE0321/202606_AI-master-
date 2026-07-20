from ..lib.logger import get_logger
from ..state import WikiAssistantState

logger = get_logger(__name__)


# Question Analyzer가 추출한 intent/entities/keywords를 바탕으로 Retriever가 임베딩할 검색 질의를 구성한다.
# 매 루프(재시도 포함)마다 실행되며, 별도 LLM 호출 없이 결정론적으로 조합한다
# (Query Rewriter가 이미 question 자체를 개선해 넘겨주므로 여기서는 entities/keywords 가중 결합만 수행).
def query_optimizer(state: WikiAssistantState) -> dict:
    logger.info("QUERY_OPTIMIZER_START")
    entities = state.get("entities", [])
    keywords = state.get("keywords", [])

    # entities는 질문에 명시된 정확한 개체명이라 검색 정밀도에 크게 기여하므로,
    # 임베딩 텍스트에서 두 번 반복해 가중치를 준다.
    entity_part = " ".join(entities)
    keyword_part = " ".join(keywords)
    search_query = " ".join(
        part for part in [entity_part, entity_part, keyword_part, state["question"]] if part
    ).strip()

    logger.info("QUERY_OPTIMIZER_RESULT search_query=%r", search_query)
    logger.info("QUERY_OPTIMIZER_END")

    return {"search_query": search_query}
