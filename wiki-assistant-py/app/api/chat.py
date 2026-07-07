import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.exception import _ERROR_BODY_DEFAULTS
from app.core.logger import get_logger
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse
from app.services.assistant_service import AssistantService

router = APIRouter()
logger = get_logger(__name__)

_service = AssistantService()


@router.post("/chat", response_model=ChatResponse, summary="AI Wiki 어시스턴트 질문")
async def chat(request: ChatRequest):
    """
    AI Wiki 어시스턴트에게 질문합니다.

    - **user_id**: 사용자 식별자
    - **question**: 질문 내용 (비어 있으면 400 반환)
    """
    try:
        # 그래프 실행은 동기(블로킹) 호출이므로 스레드로 넘겨 이벤트 루프를 막지 않는다.
        response = await asyncio.to_thread(_service.chat, request)
        return response
    except Exception as e:
        logger.error("CHAT_ERROR user_id=%s error=%s", request.user_id, str(e))
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "answer": "AI 처리 중 오류가 발생했습니다.",
                **_ERROR_BODY_DEFAULTS,
            },
        )
