from google.genai import types

from ..clients.gemini import generate_json
from ..prompts import build_answer_generator_prompt, load_system_prompt
from ..state import FinalAnswer, WikiAssistantState

_SCHEMA = {
    "type": types.Type.OBJECT,
    "properties": {
        "core_answer": {"type": types.Type.STRING},
        "detail": {"type": types.Type.STRING},
        "related_menus": {"type": types.Type.ARRAY, "items": {"type": types.Type.STRING}},
        "references": {"type": types.Type.ARRAY, "items": {"type": types.Type.STRING}},
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
    if not context.strip():
        return {"answer": _NO_CONTEXT_ANSWER, "final_message": _format_final_message(_NO_CONTEXT_ANSWER, state)}

    system_prompt = load_system_prompt()
    # 검색에는 Query Rewriter가 개선한 state["question"]을 쓰지만, 사용자에게 답할 때는 원래 질문 기준으로 답한다.
    prompt = build_answer_generator_prompt(state.get("original_question") or state["question"], context)

    answer = generate_json(prompt=prompt, schema=_SCHEMA, system_instruction=system_prompt)

    return {"answer": answer, "final_message": _format_final_message(answer, state)}
