from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from .config import config
from .nodes.answer_generator import answer_generator
from .nodes.confidence_checker import confidence_checker
from .nodes.context_builder import context_builder
from .nodes.document_reranker import document_reranker
from .nodes.query_optimizer import query_optimizer
from .nodes.query_rewriter import query_rewriter
from .nodes.question_analyzer import question_analyzer
from .nodes.wiki_retriever import wiki_retriever
from .state import WikiAssistantState


# confidence_checker가 이미 confidence_score/retry_count를 계산해두었으므로,
# 여기서는 동일한 통과 조건을 그대로 다시 평가해 다음 노드만 결정한다(부수효과 없음).
def _route_after_confidence(state: WikiAssistantState) -> str:
    passed = bool(state.get("context", "").strip()) and state.get("confidence_score", 0) >= config.confidence_threshold
    if passed:
        return END
    if state.get("retry_count", 0) <= config.max_retries:
        return "query_rewriter"
    return END


def build_graph():
    graph = StateGraph(WikiAssistantState)
    # Gemini 호출 재시도는 clients/gemini.py의 _with_retry(최대 3회)가 전담한다.
    # LangGraph 자체의 기본 노드 재시도(기본 max_attempts=3)까지 겹치면 재시도가 최대 3x4회로
    # 불어나고 로그 상 재시도 횟수가 들쭉날쭉해 보이므로, 그래프 차원의 재시도는 꺼둔다.
    graph.set_node_defaults(retry_policy=RetryPolicy(max_attempts=1))
    graph.add_node("question_analyzer", question_analyzer)
    graph.add_node("query_optimizer", query_optimizer)
    graph.add_node("wiki_retriever", wiki_retriever)
    graph.add_node("document_reranker", document_reranker)
    graph.add_node("context_builder", context_builder)
    graph.add_node("answer_generator", answer_generator)
    graph.add_node("confidence_checker", confidence_checker)
    graph.add_node("query_rewriter", query_rewriter)

    graph.add_edge(START, "question_analyzer")
    graph.add_edge("question_analyzer", "query_optimizer")
    graph.add_edge("query_optimizer", "wiki_retriever")
    graph.add_edge("wiki_retriever", "document_reranker")
    graph.add_edge("document_reranker", "context_builder")
    graph.add_edge("context_builder", "answer_generator")
    graph.add_edge("answer_generator", "confidence_checker")
    graph.add_conditional_edges(
        "confidence_checker",
        _route_after_confidence,
        {"query_rewriter": "query_rewriter", END: END},
    )
    graph.add_edge("query_rewriter", "question_analyzer")

    return graph.compile()
