from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from .config import config
from .nodes.answer_generator import answer_generator
from .nodes.confidence_checker import confidence_checker
from .nodes.context_builder import context_builder
from .nodes.document_reranker import document_reranker
from .nodes.guardrail import guardrail
from .nodes.query_optimizer import query_optimizer
from .nodes.query_rewriter import query_rewriter
from .nodes.question_analyzer import question_analyzer
from .nodes.wiki_retriever import wiki_retriever
from .state import WikiAssistantState


# Guardrail이 차단 판정을 내리면 나머지 파이프라인(LLM 호출 포함)을 전혀 거치지 않고 바로 종료한다.
def _route_after_guardrail(state: WikiAssistantState) -> str:
    return END if state.get("guardrail_triggered") else "question_analyzer"


# confidence_checker가 이미 confidence_score/retry_count를 계산해두었으므로,
# 여기서는 동일한 통과 조건을 그대로 다시 평가해 다음 노드만 결정한다(부수효과 없음).
# Context Builder는 LLM 호출이 없는 결정론적 노드라 항상 먼저 실행해도 비용이 들지 않는다.
# Confidence Checker는 그 context로 RAGAS Context Precision/Recall까지 평가해 confidence_score를 낸다:
#   통과 -> Answer Generator에서 실제 답변을 생성 (여기서 Faithfulness/Answer Relevancy도 참고용으로 평가).
#   재시도 여력 있음 -> Query Rewriter로 질문을 개선해 루프.
#   재시도 소진 -> Answer Generator를 거치지 않고 바로 담당자 안내로 종료(불필요한 LLM 호출 절약).
def _route_after_confidence(state: WikiAssistantState) -> str:
    reranked_docs = state.get("reranked_docs", [])
    passed = bool(reranked_docs) and state.get("confidence_score", 0) >= config.confidence_threshold
    if passed:
        return "answer_generator"
    if state.get("retry_count", 0) <= config.max_retries:
        return "query_rewriter"
    return END


def build_graph():
    graph = StateGraph(WikiAssistantState)
    # Gemini 호출 재시도는 clients/gemini.py의 _with_retry(최대 3회)가 전담한다.
    # LangGraph 자체의 기본 노드 재시도(기본 max_attempts=3)까지 겹치면 재시도가 최대 3x4회로
    # 불어나고 로그 상 재시도 횟수가 들쭉날쭉해 보이므로, 그래프 차원의 재시도는 꺼둔다.
    graph.set_node_defaults(retry_policy=RetryPolicy(max_attempts=1))
    graph.add_node("guardrail", guardrail)
    graph.add_node("question_analyzer", question_analyzer)
    graph.add_node("query_optimizer", query_optimizer)
    graph.add_node("wiki_retriever", wiki_retriever)
    graph.add_node("document_reranker", document_reranker)
    graph.add_node("context_builder", context_builder)
    graph.add_node("confidence_checker", confidence_checker)
    graph.add_node("answer_generator", answer_generator)
    graph.add_node("query_rewriter", query_rewriter)

    graph.add_edge(START, "guardrail")
    graph.add_conditional_edges(
        "guardrail", _route_after_guardrail, {"question_analyzer": "question_analyzer", END: END}
    )
    graph.add_edge("question_analyzer", "query_optimizer")
    graph.add_edge("query_optimizer", "wiki_retriever")
    graph.add_edge("wiki_retriever", "document_reranker")
    graph.add_edge("document_reranker", "context_builder")
    graph.add_edge("context_builder", "confidence_checker")
    graph.add_conditional_edges(
        "confidence_checker",
        _route_after_confidence,
        {"answer_generator": "answer_generator", "query_rewriter": "query_rewriter", END: END},
    )
    graph.add_edge("answer_generator", END)
    graph.add_edge("query_rewriter", "question_analyzer")

    return graph.compile()
