import time

from app.core.logger import get_logger
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse
from src.graph import build_graph

logger = get_logger(__name__)

# 그래프 컴파일은 1회만 수행하고 재사용한다 (요청마다 재빌드하지 않음).
_graph = build_graph()


class AssistantService:
    def chat(self, request: ChatRequest) -> ChatResponse:
        start = time.monotonic()

        logger.info(
            "CHAT_REQUEST user_id=%s question_len=%d",
            request.user_id,
            len(request.question),
        )

        # 재시도 루프(최대 3회) 때문에 최대 4회 반복 실행될 수 있어 recursion_limit을 넉넉히 잡는다
        # (src/ask.py CLI와 동일한 설정).
        result = _graph.invoke(
            {"question": request.question, "original_question": request.question},
            config={"recursion_limit": 50},
        )

        runtime = round(time.monotonic() - start, 3)

        logger.info(
            "CHAT_RESPONSE user_id=%s confidence=%s retry_count=%s runtime=%.3f",
            request.user_id,
            result.get("confidence_score"),
            result.get("retry_count"),
            runtime,
        )

        return ChatResponse(
            status="success",
            intent=result.get("intent"),
            keywords=result.get("keywords", []),
            answer=result.get("final_message"),
            confidence_score=result.get("confidence_score"),
            retry_count=result.get("retry_count", 0),
            runtime=runtime,
        )
