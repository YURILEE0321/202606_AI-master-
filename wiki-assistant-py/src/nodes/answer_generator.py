from ..clients.llm import generate_json
from ..lib.ragas_metrics import evaluate_answer
from ..prompts import build_answer_generator_prompt, load_system_prompt
from ..state import FinalAnswer, WikiAssistantState

_SCHEMA = {
    "type": "object",
    "properties": {
        "core_answer": {"type": "string"},
        "detail": {"type": "string"},
        "related_menus": {"type": "array", "items": {"type": "string"}},
        "references": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["core_answer", "detail", "related_menus", "references"],
}

_NO_CONTEXT_ANSWER: FinalAnswer = FinalAnswer(
    core_answer="승인된 Wiki에서 관련 정보를 찾지 못했습니다.",
    detail="질문과 일치하는 문서를 찾을 수 없어 추측된 답변을 제공하지 않습니다. 질문을 더 구체적으로 입력하시거나 담당자에게 확인해 주세요.",
    related_menus=[],
    references=[],
)


def _format_final_message(answer: FinalAnswer, state: WikiAssistantState) -> str:
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


# Confidence Checker가 이미 통과 판정을 내렸을 때만 이 노드가 실행된다(그래프에서 조건부로 연결).
# 따라서 이 시점의 context는 항상 비어있지 않지만, 방어적으로 빈 컨텍스트 케이스도 처리해둔다.
def answer_generator(state: WikiAssistantState) -> dict:
    context = state.get("context", "")
    question = state.get("original_question") or state["question"]

    if not context.strip():
        return {"answer": _NO_CONTEXT_ANSWER, "final_message": _format_final_message(_NO_CONTEXT_ANSWER, state)}

    system_prompt = load_system_prompt()
    # 검색에는 Query Rewriter가 개선한 state["question"]을 쓰지만, 사용자에게 답할 때는 원래 질문 기준으로 답한다.
    prompt = build_answer_generator_prompt(question, context)

    answer = generate_json(prompt=prompt, schema=_SCHEMA, system_instruction=system_prompt)

    # Faithfulness/Answer Relevancy는 생성된 답변이 있어야 계산 가능하므로 여기서 평가한다.
    # 이미 Confidence Checker에서 통과 판정을 내린 뒤라 재시도를 다시 트리거하진 않고, 참고/로깅용이다.
    answer_metrics = evaluate_answer(question, context, f"{answer['core_answer']} {answer['detail']}")
    faithfulness = answer_metrics["faithfulness"]
    answer_relevancy = answer_metrics["answer_relevancy"]
    ragas_full_score = (
        state.get("context_precision", 0.0) + state.get("context_recall", 0.0) + faithfulness + answer_relevancy
    ) / 4

    return {
        "answer": answer,
        "final_message": _format_final_message(answer, state),
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "ragas_full_score": ragas_full_score,
        "attempt_log": [
            f"[Answer Generator] (참고용) faithfulness={faithfulness:.2f}, answer_relevancy={answer_relevancy:.2f}, "
            f"ragas_full_score={ragas_full_score:.2f}"
        ],
    }
