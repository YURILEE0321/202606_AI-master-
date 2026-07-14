from ..clients.llm import generate_json
from ..config import config
from ..prompts import QUESTION_ANALYZER_PROMPT, build_question_analyzer_prompt
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


def _recent_turns(history: list, window_turns: int) -> list:
    """Window memory: 1턴 = 사용자+어시스턴트 한 쌍. 최근 window_turns턴만 남긴다.
    history는 항상 완결된 과거 턴만 담고 있다(현재 질문은 별도로 state["question"]에 있음)."""
    if not history:
        return []
    return history[-(window_turns * 2) :]


def question_analyzer(state: WikiAssistantState) -> dict:
    history = _recent_turns(state.get("history", []), config.history_window_turns)

    result = generate_json(
        prompt=build_question_analyzer_prompt(state["question"], history),
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
