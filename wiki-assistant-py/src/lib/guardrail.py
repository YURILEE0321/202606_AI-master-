# Input Guardrail에서 쓰는 정규식 기반 체크들 (LLM 호출 없이 무료로, 가장 먼저 실행).
# Domain Check/Permission Check(의미 판단이 필요한 항목)는 LLM 호출이 필요해 nodes/guardrail.py에서
# generate_json으로 처리한다 — 여기 있는 건 전부 결정론적 패턴 매칭뿐이다.
import re
from typing import List, Optional

# ---- Input Validation: 과도하게 긴 입력 / 비정상 포맷 ----
# 수십 MB급 텍스트도 문자 수 기준으로 걸러진다(정상적인 위키 질문은 이 범위를 넘지 않음).
MAX_QUESTION_LENGTH = 2000

# 탭(\t)/개행(\n,\r)은 정상 입력에도 나올 수 있어 제외하고, 그 외 제어 문자만 비정상으로 본다.
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# 디코딩이 깨졌을 때 흔히 나타나는 유니코드 치환 문자.
_REPLACEMENT_CHAR = "�"


def validate_input(question: str) -> Optional[str]:
    """길이/포맷 이상을 검사한다. 문제가 있으면 사유를, 없으면 None을 반환한다."""
    if not question.strip():
        return "빈 입력"
    if len(question) > MAX_QUESTION_LENGTH:
        return f"입력 길이 초과({len(question)}자 > {MAX_QUESTION_LENGTH}자)"
    if _REPLACEMENT_CHAR in question:
        return "손상된 인코딩(replacement character) 포함"
    if _CONTROL_CHAR_PATTERN.search(question):
        return "비정상 제어 문자 포함"
    return None


# ---- Prompt Injection: 시스템 프롬프트 노출 시도 / 이전 지시 무시 지시 ----
# 위키 도메인(설비/메뉴/용어) 질문에서는 자연스럽게 나오기 어려운 표현만 포함해 오탐(false positive)을 줄인다.
_INJECTION_PATTERNS = [
    r"시스템\s*프롬프트",
    r"system\s*prompt",
    r"이전\s*지시.{0,10}(무시|잊)",
    r"지금까지의?\s*(지시|명령|규칙).{0,10}(무시|잊)",
    r"ignore\s+(all\s+)?(the\s+)?(previous|above)\s+instructions",
    r"너는\s*이제부터",
    r"you\s+are\s+now",
    r"act\s+as\s+(a|an)?\s*\w*\s*(ai|assistant)?\s*(without|no)\s+restrictions",
    r"역할\s*(을|를)?\s*무시",
    r"jailbreak",
    r"\bDAN\b",
    r"개발자\s*모드",
    r"developer\s*mode",
    r"원본\s*(프롬프트|지시문|설정)",
    # 어미(을/를 + 알려/보여 등)를 특정하지 않고 "너의/네 + 규칙/지침/지시사항/프롬프트"만으로 매칭한다
    # — "너의 규칙이 뭐야"처럼 다른 어미로 물어도 잡히도록. "설정"은 own 도메인의 실제 메뉴명(Settings)과
    # 겹쳐 오탐이 나므로 이 패턴에서는 제외한다(원본 설정 패턴은 별도로 이미 있음).
    r"(너의|네)\s*(규칙|지침|지시사항|명령)",
    r"reveal\s+your\s+(instructions|prompt|system)",
    r"what\s+(are\s+)?your\s+(rules|instructions|guidelines)",
]
_COMPILED_INJECTION = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def detect_injection(question: str) -> Optional[str]:
    """정책 기반 키워드/패턴 탐지. 매칭된 패턴 문자열을 반환하고, 없으면 None."""
    for pattern in _COMPILED_INJECTION:
        if pattern.search(question):
            return pattern.pattern
    return None


# ---- PII Detection: 개인정보 포함 여부 ----
# 질문 텍스트가 그대로 외부 LLM API로 전송되므로, 개인정보가 섞여 있으면 전송 전에 걸러낸다.
_PII_PATTERNS = {
    "주민등록번호": re.compile(r"\d{6}[-\s]?[1-4]\d{6}"),
    "이메일": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "휴대폰번호": re.compile(r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}"),
    "신용카드번호": re.compile(r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"),
}


def detect_pii(question: str) -> List[str]:
    """탐지된 개인정보 유형 목록을 반환한다(없으면 빈 리스트)."""
    return [label for label, pattern in _PII_PATTERNS.items() if pattern.search(question)]
