from ..clients.llm import generate_json
from ..prompts import QUESTION_ANALYZER_PROMPT
from ..state import WikiAssistantState

_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["기능문의", "용어", "메뉴/업무절차", "데이터유입문제", "기타"],
        },
        "entities": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["intent", "entities", "keywords"],
}


def question_analyzer(state: WikiAssistantState) -> dict:
    result = generate_json(
        prompt=f"질문: {state['question']}",
        schema=_SCHEMA,
        system_instruction=QUESTION_ANALYZER_PROMPT,
    )

    return {
        # 최초 진입 시에만 채워지고, 이후 루프에서는 기존 값을 유지한다.
        "original_question": state.get("original_question") or state["question"],
        "intent": result["intent"],
        "entities": result["entities"],
        "keywords": result["keywords"],
    }
