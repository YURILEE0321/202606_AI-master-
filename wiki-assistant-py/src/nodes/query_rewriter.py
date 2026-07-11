from ..clients.llm import generate_json
from ..prompts import build_multi_query_prompt, build_query_expansion_prompt, build_query_rewriting_prompt
from ..state import WikiAssistantState

_REWRITE_SCHEMA = {
    "type": "object",
    "properties": {"rewritten_question": {"type": "string"}},
    "required": ["rewritten_question"],
}

_EXPANSION_SCHEMA = {
    "type": "object",
    "properties": {
        "expanded_question": {"type": "string"},
        "related_terms": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["expanded_question", "related_terms"],
}

_MULTI_QUERY_SCHEMA = {
    "type": "object",
    "properties": {"variants": {"type": "array", "items": {"type": "string"}}},
    "required": ["variants"],
}


# retry_count는 confidence_checker에서 이미 +1 된 값으로 들어온다 (1 -> Query Rewriting,
# 2 -> Query Expansion, 3 -> Multi Query Retrieval).
def query_rewriter(state: WikiAssistantState) -> dict:
    original_question = state.get("original_question") or state["question"]
    keywords = state.get("keywords", [])
    entities = state.get("entities", [])
    context = state.get("context", "")
    attempt = state.get("retry_count", 0)

    if attempt == 1:
        result = generate_json(
            prompt=build_query_rewriting_prompt(original_question, keywords, entities, context),
            schema=_REWRITE_SCHEMA,
        )
        rewritten = result["rewritten_question"]
        return {
            "question": rewritten,
            "query_variants": [],
            "last_rewrite_technique": "Query Rewriting",
            "attempt_log": [f'[재시도 {attempt}/Query Rewriting] "{rewritten}"'],
        }

    if attempt == 2:
        result = generate_json(
            prompt=build_query_expansion_prompt(original_question, keywords, entities, context),
            schema=_EXPANSION_SCHEMA,
        )
        expanded = result["expanded_question"]
        related_terms = result["related_terms"]
        return {
            "question": expanded,
            "query_variants": [],
            "last_rewrite_technique": "Query Expansion",
            "attempt_log": [
                f'[재시도 {attempt}/Query Expansion] "{expanded}" (관련 용어: {", ".join(related_terms)})'
            ],
        }

    result = generate_json(
        prompt=build_multi_query_prompt(original_question, keywords, entities, context),
        schema=_MULTI_QUERY_SCHEMA,
    )
    variants = result["variants"]
    return {
        "question": original_question,
        "query_variants": variants,
        "last_rewrite_technique": "Multi Query Retrieval",
        "attempt_log": [f"[재시도 {attempt}/Multi Query Retrieval] {' | '.join(variants)}"],
    }
