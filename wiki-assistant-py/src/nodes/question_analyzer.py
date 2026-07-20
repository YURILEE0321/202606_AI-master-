from ..clients.llm import generate_json
from ..config import config
from ..lib.history import recent_turns
from ..lib.logger import get_logger
from ..prompts import QUESTION_ANALYZER_PROMPT, build_question_analyzer_prompt
from ..state import WikiAssistantState

logger = get_logger(__name__)

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
    history = recent_turns(state.get("history", []), config.history_window_turns)
    logger.info(
        "QUESTION_ANALYZER_START question_len=%d history_turns=%d",
        len(state["question"]),
        len(history) // 2,
    )

    result = generate_json(
        prompt=build_question_analyzer_prompt(state["question"], history),
        schema=_SCHEMA,
        system_instruction=QUESTION_ANALYZER_PROMPT,
    )

    logger.info(
        "QUESTION_ANALYZER_RESULT intent=%s entities=%s keywords=%s",
        result["intent"],
        result["entities"],
        result["keywords"],
    )
    logger.info("QUESTION_ANALYZER_END")

    return {
        # 최초 진입 시에만 채워지고, 이후 루프에서는 기존 값을 유지한다.
        "original_question": state.get("original_question") or state["question"],
        "intent": result["intent"],
        "entities": result["entities"],
        "keywords": result["keywords"],
    }
