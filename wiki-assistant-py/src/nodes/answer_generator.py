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


def answer_generator(state: WikiAssistantState) -> dict:
    context = state.get("context", "")
    if not context.strip():
        return {"answer": _NO_CONTEXT_ANSWER}

    system_prompt = load_system_prompt()
    # 검색에는 Query Rewriter가 개선한 state["question"]을 쓰지만, 사용자에게 답할 때는 원래 질문 기준으로 답한다.
    prompt = build_answer_generator_prompt(state.get("original_question") or state["question"], context)

    answer = generate_json(prompt=prompt, schema=_SCHEMA, system_instruction=system_prompt)

    return {"answer": answer}
