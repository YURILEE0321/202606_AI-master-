from pathlib import Path
from typing import List

from .lib.history import format_history_block

_SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "AI Wiki Assistant Agent - System Prompt.md"
)


def load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


QUESTION_ANALYZER_PROMPT = """당신은 AI Wiki Assistant의 Question Analyzer 노드이다.
사용자의 자연어 질문을 분석하여 의도(intent), 개체명(entities), 검색에 사용할 핵심 키워드(keywords)를 추출한다.

intent는 다음 중 하나로 분류한다: "기능문의", "용어", "메뉴/업무절차", "데이터유입문제", "기타".

entities는 질문에 명시적으로 등장하는 구체적인 고유명사를 추출한다
(예: 메뉴명 Settings/Review/Model/Deployment/Monitoring, 용어 GOOD/DEFECT/Confidence/Lot/Recipe,
시스템·설비명, 코드/ID 등). 일반적인 서술어나 추상적인 표현은 entities에 넣지 않는다. 없으면 빈 배열을 반환한다.

이전 대화가 함께 주어지면, 현재 질문의 지시어("여기서", "그거", "이전에 말한 것" 등)나 생략된 주어가
가리키는 대상을 이전 대화에서 찾아 entities에 포함하라. 이 지시어 해석은 반드시 이전 대화에 실제로
언급된 대상으로만 채운다 — 질문에 등장하는 다른 단어(예: "배포")와 의미상 관련 있어 보인다는 이유로
이전 대화에 없던 별개의 개체(예: "Deployment")를 지어내 지시어의 대상인 것처럼 넣지 마라. 그런
연관 개체는 entities가 아니라 keywords에만 넣는다. 이전 대화와 무관하거나 지시 대상이 불명확하면
추측해서 채우지 마라.

keywords는 질문에 등장하는 메뉴명, 기능명, 용어, 설정명 등 검색에 유용한 명사구 위주로 3~6개 추출한다
(entities보다 넓은 범위로, 동의어나 관련어를 포함해도 된다). 지시어로 이전 대화의 대상을 참조하는
경우 그 대상도 keywords에 포함하라."""


def build_question_analyzer_prompt(question: str, history: List[dict]) -> str:
    history_block = format_history_block(history)
    if not history_block:
        return f"질문: {question}"

    return f"""이전 대화:
{history_block}

현재 질문: {question}"""


def build_answer_generator_prompt(question: str, context: str, history: List[dict] = None) -> str:
    history_block = format_history_block(history or [])
    history_section = f"\n이전 대화:\n{history_block}\n" if history_block else ""

    if not context.strip():
        return f"""{history_section}
사용자 질문: {question}

승인된 AI Wiki에서 관련 문서를 찾지 못했다. 추측하지 말고 정보가 부족함을 안내하고 추가 정보를 요청하는 답변을 생성하라."""

    scope_instruction = (
        "질문에 \"여기서\", \"그거\" 같은 지시어가 있고 이전 대화가 함께 주어졌다면, 그 지시어가 가리키는 "
        "대상(예: 이전에 논의한 메뉴)이 실제로 그 기능을 지원하는지 컨텍스트에서 확인하라. 지원하지 않고 "
        "다른 메뉴/기능을 통해서만 가능하다면, \"거기서는 안 되고 ○○에서 가능하다\"처럼 그 차이를 답변에 "
        "명확히 밝혀라. 지시어를 문맥과 무관하게 플랫폼 전체에 대한 일반 질문으로 뭉뚱그려 답하지 마라.\n\n"
        if history_block
        else ""
    )

    return f"""{history_section}
사용자 질문: {question}

아래는 승인된 AI Wiki에서 검색된 관련 문서 컨텍스트이다. 이 내용만 근거로 답변하라. 컨텍스트에 없는 내용은 추측하지 마라.

{scope_instruction}--- 컨텍스트 시작 ---
{context}
--- 컨텍스트 끝 ---

답변 형식에 맞춰 핵심 답변(core_answer), 상세 설명(detail), 관련 메뉴/업무 절차(related_menus), 참고 출처(references)를 작성하라."""


# ---- Query Rewriter (재시도 루프 전용, 시도 차수별로 다른 기법을 사용) ----

_DOMAIN_HINT = (
    "이 시스템은 AI Defect Inspection / AI 비전 검사 플랫폼에 대한 Wiki이며, "
    "설비관리·이미지 조회·AI 평가·리뷰·모델관리·Settings·Review·Model·Deployment·Monitoring 등의 메뉴와 "
    "GOOD/DEFECT, Confidence, Lot, Recipe 같은 용어를 다룬다."
)

# 질문이 플랫폼과 무관한 경우(날씨, 잡담 등) 관련성을 억지로 만들어내면 벡터 유사도만 부풀려
# 실제로는 답할 수 없는 질문의 confidence가 잘못 통과되는 문제가 생긴다. 이를 막기 위한 공통 가드.
_OUT_OF_DOMAIN_GUARD = (
    "주의: 질문이 위 플랫폼 도메인과 명백히 무관한 주제(예: 날씨, 일반 상식, 잡담 등)라면, "
    "억지로 플랫폼 용어를 끌어다 붙이지 마라. 이 경우 질문을 원문 그대로 두고 관련 용어는 빈 목록으로 반환하라."
)


def _attempt_context(keywords: List[str], entities: List[str], context: str) -> str:
    keyword_line = f"이전 시도 키워드: {', '.join(keywords)}" if keywords else "이전 시도에서 추출된 키워드 없음"
    entity_line = f"이전 시도 개체명: {', '.join(entities)}" if entities else "이전 시도에서 추출된 개체명 없음"
    context_line = (
        "이전 검색에서 일부 문서를 찾았지만 신뢰도가 기준에 미달했다."
        if context.strip()
        else "이전 검색에서 관련 문서를 전혀 찾지 못했다."
    )
    return f"{keyword_line}\n{entity_line}\n{context_line}"


def build_query_rewriting_prompt(
    original_question: str, keywords: List[str], entities: List[str], context: str
) -> str:
    return f"""당신은 AI Wiki Assistant의 Query Rewriter이다(1차 재시도, 기법: Query Rewriting).
아래 원본 질문의 검색 신뢰도가 낮아 재검색이 필요하다. {_DOMAIN_HINT}
{_OUT_OF_DOMAIN_GUARD}

원본 질문: {original_question}
{_attempt_context(keywords, entities, context)}

원본 질문의 의도는 유지하되, 모호한 표현을 구체화하고 플랫폼 용어(위 힌트 참고)로 바꾸어 검색에 더 적합한 한 문장으로 다시 작성하라.
개체명(entities)이 있다면 그 표현을 최대한 살려서 재작성하라."""


def build_query_expansion_prompt(
    original_question: str, keywords: List[str], entities: List[str], context: str
) -> str:
    return f"""당신은 AI Wiki Assistant의 Query Rewriter이다(2차 재시도, 기법: Query Expansion).
아래 원본 질문에 관련 동의어/상위어/하위어/플랫폼 용어를 추가하여 검색 범위를 넓힌 확장 질의를 만들어라. {_DOMAIN_HINT}
{_OUT_OF_DOMAIN_GUARD} (이 경우 expanded_question에 원본 질문만 그대로 담고 related_terms는 빈 배열로 반환하라.)

원본 질문: {original_question}
{_attempt_context(keywords, entities, context)}

확장 질의(expanded_question)는 원본 질문 문장 뒤에 관련 용어를 자연스럽게 덧붙인 형태로 작성하고,
related_terms에는 추가한 관련 용어 목록을 나열하라. 단, 원본 질문과 실제로 관련 있는 용어만 추가하라."""


def build_multi_query_prompt(
    original_question: str, keywords: List[str], entities: List[str], context: str
) -> str:
    return f"""당신은 AI Wiki Assistant의 Query Rewriter이다(3차 재시도, 기법: Multi Query Retrieval).
아래 원본 질문에 대해 서로 다른 관점/표현의 검색 질의를 3개 생성하라. {_DOMAIN_HINT}
각 질의는 서로 겹치지 않는 각도(동의어, 상위 개념, 세부 절차 등)로 작성한다.
{_OUT_OF_DOMAIN_GUARD} (이 경우 variants에 원본 질문만 그대로 담아 반환하라.)

원본 질문: {original_question}
{_attempt_context(keywords, entities, context)}"""
