from ..config import config
from ..lib.ragas_metrics import evaluate_context
from ..state import WikiAssistantState

# Final Score = similarity_score * SIMILARITY_WEIGHT + ragas_score * RAGAS_WEIGHT
# RAGAS 쪽에 더 높은 가중치를 준다: similarity_score는 top-1 청크의 벡터 유사도 하나뿐이라
# "그럴듯하지만 실제로는 무관한" 검색에 취약한 반면(과거 도메인 무관 질의에서 실제로 겪은 문제),
# RAGAS의 context_recall은 검색된 문서 "전체"가 질문에 답하기 충분한 정보를 담고 있는지까지 LLM이
# 직접 판단해 similarity_score가 못 보는 실패 모드를 잡아준다. 다만 similarity_score도 비용 없이
# 이미 계산돼 있고 LLM 판단의 노이즈를 보정하는 역할을 하므로 완전히 배제하지 않는다.
_SIMILARITY_WEIGHT = 0.4
_RAGAS_WEIGHT = 0.6


# confidence는 Similarity Score(top-1 벡터 유사도)와 RAGAS 사전 지표(Context Precision/Recall)의
# 가중 평균이다. 이 시점엔 아직 답변이 없어 Faithfulness/Answer Relevancy는 계산할 수 없으므로,
# 그 둘은 Answer Generator가 답변 확정 후 참고용으로만 평가한다(재시도 트리거에는 반영 안 함).
#
# confidence >= threshold: Answer Generator로 진행해 답변을 생성한다.
# confidence < threshold: retry_count를 올리고, max_retries 이내면 Query Rewriter로 보낸다
#   (라우팅은 graph.py의 조건부 엣지가 담당). max_retries를 넘기면 담당자 문의 안내를
#   final_message로 확정하고, 불필요한 Answer Generator 호출 없이 바로 종료한다.
def confidence_checker(state: WikiAssistantState) -> dict:
    reranked_docs = state.get("reranked_docs", [])
    similarity_score = max(0.0, min(1.0, reranked_docs[0]["score"] if reranked_docs else 0.0))

    context = state.get("context", "")
    context_metrics = evaluate_context(state.get("original_question") or state["question"], context)
    context_precision = context_metrics["context_precision"]
    context_recall = context_metrics["context_recall"]
    ragas_score = (context_precision + context_recall) / 2

    confidence_score = _SIMILARITY_WEIGHT * similarity_score + _RAGAS_WEIGHT * ragas_score

    metrics = {
        "similarity_score": similarity_score,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "ragas_score": ragas_score,
        "confidence_score": confidence_score,
    }
    metrics_log = (
        f"similarity={similarity_score:.2f}, context_precision={context_precision:.2f}, "
        f"context_recall={context_recall:.2f}, ragas={ragas_score:.2f} → confidence={confidence_score:.2f}"
    )

    passed = bool(reranked_docs) and confidence_score >= config.confidence_threshold

    if passed:
        return {
            **metrics,
            "escalation_required": False,
            "attempt_log": [f"[Confidence Checker] {metrics_log} >= {config.confidence_threshold} → 답변 생성 진행"],
        }

    next_retry_count = state.get("retry_count", 0) + 1

    if next_retry_count <= config.max_retries:
        return {
            **metrics,
            "retry_count": next_retry_count,
            "escalation_required": False,
            "attempt_log": [
                f"[Confidence Checker] {metrics_log} < {config.confidence_threshold} "
                f"→ 재시도 {next_retry_count}/{config.max_retries} 진행"
            ],
        }

    return {
        **metrics,
        "retry_count": next_retry_count,
        "escalation_required": True,
        "final_message": "질문에 해당하는 답변을 찾지 못했습니다. 담당자에게 문의 부탁드립니다.",
        "attempt_log": [
            f"[Confidence Checker] {metrics_log} < {config.confidence_threshold} "
            f"→ 재시도 소진({next_retry_count}) → 담당자 문의 안내"
        ],
    }
