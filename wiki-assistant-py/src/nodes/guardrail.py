from ..clients.llm import generate_json
from ..lib.guardrail import detect_injection, detect_pii, validate_input
from ..lib.logger import get_logger
from ..prompts import GUARDRAIL_PROMPT, GUARDRAIL_PROXY_PROMPT, build_guardrail_proxy_prompt
from ..state import WikiAssistantState

logger = get_logger(__name__)

_OWN_SCHEMA = {
    "type": "object",
    "properties": {
        "domain_relevant": {"type": "boolean"},
        "permission_required": {"type": "boolean"},
        "reasoning": {"type": "string"},
    },
    "required": ["domain_relevant", "permission_required", "reasoning"],
}

# proxy도 domain_relevant를 판단하지만, 하드코딩된 도메인이 아니라 그 space에 실제로 승인된 문서
# 제목 목록을 근거로 판단한다(build_guardrail_proxy_prompt가 프롬프트에 제목을 실어 보냄).
_PROXY_SCHEMA = _OWN_SCHEMA

_MESSAGES = {
    "input_validation": "요청을 처리할 수 없습니다. 입력 내용을 확인한 뒤 다시 시도해 주세요.",
    "prompt_injection": "승인된 문서와 관련된 질문에만 답변드릴 수 있어요. 플랫폼 사용법이나 용어에 대해 다시 질문해 주세요.",
    "pii": "개인정보가 포함된 것으로 보이는 내용은 처리할 수 없어요. 개인정보를 제외하고 다시 질문해 주세요.",
    "domain": "승인된 문서와 관련된 질문에만 답변드릴 수 있어요. 사용법이나 용어에 대해 다시 질문해 주세요.",
    "permission": "권한이 필요한 정보는 안내해드릴 수 없어요. 담당자에게 문의해 주세요.",
}


def _blocked(reason: str) -> dict:
    logger.info("GUARDRAIL_END result=blocked reason=%s", reason)
    return {
        "guardrail_triggered": True,
        "guardrail_reason": reason,
        "final_message": _MESSAGES[reason],
    }


# 파이프라인 최초 진입점(START 직후, Question Analyzer보다 앞). 5가지를 순서대로 검사하고,
# 하나라도 걸리면 이후 노드(LLM 호출 포함)를 전혀 거치지 않고 바로 고정 안내 메시지로 종료한다.
# 앞의 3개(Input Validation/Prompt Injection/PII)는 정규식만으로 판단 가능해 LLM 호출 없이 무료로
# 먼저 걸러내고, 의미 판단이 필요한 나머지 2개(Domain/Permission Check)만 LLM 호출 1회로 같이 묶어
# 처리한다 — 재시도 루프(Query Rewriter -> Question Analyzer)에는 이 노드를 다시 통과시키지 않는다
# (재작성된 질문은 우리 시스템이 만든 신뢰된 텍스트이지 사용자 원문이 아니기 때문).
def guardrail(state: WikiAssistantState) -> dict:
    question = state["question"]
    # Domain Check는 own 위키(AI Defect Inspection 플랫폼)는 하드코딩된 도메인 설명으로,
    # proxy(space 기반, backend-proxy의 실제 데이터, 도메인이 space마다 전혀 다름 — 예: StarRocks,
    # Spark)는 그 space에 실제로 승인된 문서 제목 목록(state["doc_id_map"])을 근거로 판단한다.
    # "날씨/잡담처럼 문서 제목과 명백히 무관"할 때만 차단하고 애매하면 통과시키므로, 완전히 무관한
    # 질문은 Question Analyzer 이후 단계(비용이 드는 재시도 루프)까지 안 가고 여기서 바로 끝난다.
    is_proxy = bool(state.get("space_id"))
    logger.info("GUARDRAIL_START question_len=%d proxy=%s", len(question), is_proxy)

    reason = validate_input(question)
    if reason:
        logger.info("GUARDRAIL_BLOCKED check=input_validation reason=%s", reason)
        return _blocked("input_validation")

    matched = detect_injection(question)
    if matched:
        logger.info("GUARDRAIL_BLOCKED check=prompt_injection pattern=%r", matched)
        return _blocked("prompt_injection")

    pii_found = detect_pii(question)
    if pii_found:
        logger.info("GUARDRAIL_BLOCKED check=pii found=%s", pii_found)
        return _blocked("pii")

    if is_proxy:
        doc_titles = [info.get("title", "") for info in state.get("doc_id_map", {}).values() if info.get("title")]
        result = generate_json(
            prompt=build_guardrail_proxy_prompt(question, doc_titles),
            schema=_PROXY_SCHEMA,
            system_instruction=GUARDRAIL_PROXY_PROMPT,
        )
    else:
        result = generate_json(prompt=f"질문: {question}", schema=_OWN_SCHEMA, system_instruction=GUARDRAIL_PROMPT)

    logger.info(
        "GUARDRAIL_SEMANTIC_RESULT domain_relevant=%s permission_required=%s reasoning=%r",
        result["domain_relevant"],
        result["permission_required"],
        result["reasoning"],
    )

    if not result["domain_relevant"]:
        return _blocked("domain")
    if result["permission_required"]:
        return _blocked("permission")

    logger.info("GUARDRAIL_PASSED question_len=%d", len(question))
    logger.info("GUARDRAIL_END result=passed")
    return {"guardrail_triggered": False}
