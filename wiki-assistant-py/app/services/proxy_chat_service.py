import time
from typing import Dict

from app.core.logger import get_logger
from app.schemas.proxy_chat import ProxyChatRequest, ProxyChatResponse, ProxySource
from src.clients import proxy_db
from src.graph import build_graph

logger = get_logger(__name__)

_graph = build_graph()

# 2026_aimaster_wikigen의 assistant가 쓰던 문구와 동일하게 맞춘다(assistant/app/graph/nodes.py::NO_CONTEXT_TEXT).
_NO_APPROVED_DOCS_TEXT = "관련된 승인 문서를 찾지 못했어요."


class ProxyChatService:
    def chat(self, request: ProxyChatRequest) -> ProxyChatResponse:
        start = time.monotonic()

        logger.info(
            "PROXY_CHAT_REQUEST space_id=%s question_len=%d",
            request.space_id,
            len(request.question),
        )

        doc_id_map = proxy_db.get_allowed_documents(request.space_id)
        if not doc_id_map:
            logger.info("PROXY_CHAT_NO_APPROVED_DOCS space_id=%s", request.space_id)
            return ProxyChatResponse(answer=_NO_APPROVED_DOCS_TEXT, sources=[])

        # history는 request.history 전체를 그대로 상태에 넣고, Question Analyzer가 최근
        # HISTORY_WINDOW_TURNS(기본 5턴)만 잘라 써서(window memory) 지시어/생략된 주어를 해석한다
        # (src/nodes/question_analyzer.py::_recent_turns). 전체 대화가 10턴 이상으로 길어져도
        # 프롬프트에 들어가는 대화 맥락 크기는 늘지 않는다.
        result = _graph.invoke(
            {
                "question": request.question,
                "original_question": request.question,
                "space_id": request.space_id,
                "history": [turn.model_dump() for turn in request.history],
                "allowed_doc_ids": list(doc_id_map.keys()),
                "doc_id_map": doc_id_map,
            },
            config={"recursion_limit": 50},
        )

        runtime = round(time.monotonic() - start, 3)

        answer = result.get("answer")
        if answer:
            answer_text = answer["core_answer"] + "\n\n" + answer["detail"]
            if answer.get("related_menus"):
                answer_text += "\n\n관련 메뉴/업무 절차: " + ", ".join(answer["related_menus"])
        else:
            answer_text = result.get("final_message") or _NO_APPROVED_DOCS_TEXT

        doc_scores: Dict[str, float] = {}
        for doc in result.get("reranked_docs", []):
            doc_id = doc["doc_id"]
            doc_scores[doc_id] = max(doc_scores.get(doc_id, 0.0), doc["score"])

        sources = [
            ProxySource(document_id=mapped["document_id"], title=mapped["title"], score=doc_scores[doc_id])
            for doc_id, mapped in doc_id_map.items()
            if doc_id in doc_scores
        ]
        sources.sort(key=lambda s: s.score, reverse=True)

        logger.info(
            "PROXY_CHAT_RESPONSE space_id=%s confidence=%s retry_count=%s sources=%d runtime=%.3f",
            request.space_id,
            result.get("confidence_score"),
            result.get("retry_count"),
            len(sources),
            runtime,
        )

        return ProxyChatResponse(answer=answer_text, sources=sources)
