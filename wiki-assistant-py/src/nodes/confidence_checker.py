from ..config import config
from ..state import WikiAssistantState


# confidence는 검색 점수(reranked_docs)만으로 계산되며 Answer Generator보다 먼저 실행된다.
# confidence >= threshold: Context Builder -> Answer Generator로 진행해 답변을 생성한다.
# confidence < threshold: retry_count를 올리고, max_retries 이내면 Query Rewriter로 보낸다
#   (라우팅은 graph.py의 조건부 엣지가 담당). max_retries를 넘기면 담당자 문의 안내를
#   final_message로 확정하고, 불필요한 Answer Generator 호출 없이 바로 종료한다.
def confidence_checker(state: WikiAssistantState) -> dict:
    reranked_docs = state.get("reranked_docs", [])
    top_score = reranked_docs[0]["score"] if reranked_docs else 0.0
    confidence_score = max(0.0, min(1.0, top_score))
    passed = bool(reranked_docs) and confidence_score >= config.confidence_threshold

    if passed:
        return {
            "confidence_score": confidence_score,
            "escalation_required": False,
            "attempt_log": [
                f"[Confidence Checker] confidence={confidence_score:.2f} >= {config.confidence_threshold} "
                "→ 답변 생성 진행"
            ],
        }

    next_retry_count = state.get("retry_count", 0) + 1

    if next_retry_count <= config.max_retries:
        return {
            "confidence_score": confidence_score,
            "retry_count": next_retry_count,
            "escalation_required": False,
            "attempt_log": [
                f"[Confidence Checker] confidence={confidence_score:.2f} < {config.confidence_threshold} "
                f"→ 재시도 {next_retry_count}/{config.max_retries} 진행"
            ],
        }

    return {
        "confidence_score": confidence_score,
        "retry_count": next_retry_count,
        "escalation_required": True,
        "final_message": "질문에 해당하는 답변을 찾지 못했습니다. 담당자에게 문의 부탁드립니다.",
        "attempt_log": [
            f"[Confidence Checker] confidence={confidence_score:.2f} < {config.confidence_threshold} "
            f"→ 재시도 소진({next_retry_count}) → 담당자 문의 안내"
        ],
    }
