from ..config import config
from ..state import WikiAssistantState


def _format_answer(state: WikiAssistantState) -> str:
    answer = state.get("answer")
    if not answer:
        return "답변을 생성하지 못했습니다."

    source_lines = "\n".join(f"- {s['title']} ({s['source_file']})" for s in state.get("sources", []))

    parts = [
        f"[핵심 답변]\n{answer['core_answer']}",
        f"[상세 설명]\n{answer['detail']}",
    ]
    if answer["related_menus"]:
        parts.append(f"[관련 메뉴/업무 절차]\n{', '.join(answer['related_menus'])}")
    if source_lines:
        parts.append(f"[참고 출처]\n{source_lines}")

    return "\n\n".join(parts)


# confidence >= threshold: 답변 확정.
# confidence < threshold: retry_count를 올리고, max_retries 이내면 Query Rewriter로 보낼 수 있도록
#   escalation_required=False로 둔 채 리턴(라우팅은 graph.py의 조건부 엣지가 retry_count로 판단한다).
#   max_retries를 넘기면 담당자 문의 안내를 final_message로 확정한다.
def confidence_checker(state: WikiAssistantState) -> dict:
    reranked_docs = state.get("reranked_docs", [])
    top_score = reranked_docs[0]["score"] if reranked_docs else 0.0
    confidence_score = max(0.0, min(1.0, top_score))
    has_context = bool(state.get("context", "").strip())
    passed = has_context and confidence_score >= config.confidence_threshold

    if passed:
        return {
            "confidence_score": confidence_score,
            "escalation_required": False,
            "final_message": _format_answer(state),
            "attempt_log": [
                f"[Confidence Checker] confidence={confidence_score:.2f} >= {config.confidence_threshold} → 답변 확정"
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
