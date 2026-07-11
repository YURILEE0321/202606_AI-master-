# RAGAS(Retrieval-Augmented Generation Assessment) 스타일 지표를 LLM 심사로 근사한다.
# 실제 ragas 패키지는 Context Recall 계산에 ground_truth(정답 레퍼런스)를 요구하는데,
# 이 프로젝트는 라이브 사용자 질문을 다루므로 정답 레퍼런스가 없다. 그래서 ragas 패키지 대신
# 우리가 이미 쓰고 있는 provider-neutral generate_json으로 레퍼런스 없이(reference-free) 심사한다.
from typing import TypedDict

from ..clients.llm import generate_json


class ContextMetrics(TypedDict):
    context_precision: float
    context_recall: float


class AnswerMetrics(TypedDict):
    faithfulness: float
    answer_relevancy: float


_CONTEXT_METRICS_SCHEMA = {
    "type": "object",
    "properties": {
        "context_precision": {"type": "number"},
        "context_recall": {"type": "number"},
        "reasoning": {"type": "string"},
    },
    "required": ["context_precision", "context_recall", "reasoning"],
}

_ANSWER_METRICS_SCHEMA = {
    "type": "object",
    "properties": {
        "faithfulness": {"type": "number"},
        "answer_relevancy": {"type": "number"},
        "reasoning": {"type": "string"},
    },
    "required": ["faithfulness", "answer_relevancy", "reasoning"],
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def evaluate_context(question: str, context: str) -> ContextMetrics:
    """Context Precision / Context Recall을 LLM 심사로 0.0~1.0 사이 값으로 평가한다.
    답변 생성 전(retrieved context만으로) 계산 가능해 Confidence Checker의 사전 검사에 쓴다."""
    if not context.strip():
        return {"context_precision": 0.0, "context_recall": 0.0}

    prompt = f"""당신은 RAG 시스템의 검색(Retrieval) 품질을 평가하는 평가자이다.
정답 레퍼런스 없이, 질문과 검색된 컨텍스트만 보고 판단하라.

[질문]
{question}

[검색된 컨텍스트]
{context}

다음 두 지표를 0.0~1.0 사이 실수로 평가하라:
- context_precision: 검색된 내용 중 이 질문에 실제로 관련 있는 부분의 비율. 관련 없는 내용이 섞여 있으면 낮게 준다.
- context_recall: 이 질문에 답하기 위해 필요한 정보가 컨텍스트에 충분히 포함되어 있는지. 핵심 정보가 빠져 있으면 낮게 준다.
"""
    result = generate_json(prompt=prompt, schema=_CONTEXT_METRICS_SCHEMA)
    return {
        "context_precision": _clamp(float(result["context_precision"])),
        "context_recall": _clamp(float(result["context_recall"])),
    }


def evaluate_answer(question: str, context: str, answer_text: str) -> AnswerMetrics:
    """Faithfulness / Answer Relevancy를 LLM 심사로 0.0~1.0 사이 값으로 평가한다.
    생성된 답변이 있어야 계산 가능하므로, 답변 확정 후 참고용 로깅에만 사용한다(재시도 트리거 아님)."""
    prompt = f"""당신은 RAG 시스템의 답변(Generation) 품질을 평가하는 평가자이다.

[질문]
{question}

[검색된 컨텍스트]
{context}

[생성된 답변]
{answer_text}

다음 두 지표를 0.0~1.0 사이 실수로 평가하라:
- faithfulness: 답변에 담긴 주장들이 컨텍스트에 실제로 근거하는 비율. 컨텍스트에 없는 내용을 지어냈으면 낮게 준다.
- answer_relevancy: 답변이 질문의 요지에 얼마나 적절하게 대응하는지. 질문과 무관하거나 핵심을 벗어났으면 낮게 준다.
"""
    result = generate_json(prompt=prompt, schema=_ANSWER_METRICS_SCHEMA)
    return {
        "faithfulness": _clamp(float(result["faithfulness"])),
        "answer_relevancy": _clamp(float(result["answer_relevancy"])),
    }
