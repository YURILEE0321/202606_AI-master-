import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.logger import get_logger
from app.schemas.proxy_chat import ProxyChatRequest, ProxyChatResponse
from app.services.proxy_chat_service import ProxyChatService

router = APIRouter()
logger = get_logger(__name__)

_service = ProxyChatService()


@router.post(
    "/assistant/v1/chat",
    response_model=ProxyChatResponse,
    summary="2026_aimaster_wikigen backend-proxy 호환 채팅 엔드포인트",
)
async def proxy_chat(request: ProxyChatRequest):
    """
    2026_aimaster_wikigen의 assistant 서비스를 대체하는 엔드포인트.
    backend-proxy가 그대로 호출할 수 있도록 요청/응답 계약을 동일하게 맞췄다
    (assistant/app/schemas.py 참고).
    """
    try:
        response = await asyncio.to_thread(_service.chat, request)
        return response
    except Exception as e:
        logger.error("PROXY_CHAT_ERROR space_id=%s error=%s", request.space_id, str(e))
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "ASSISTANT_ERROR", "message": "답변 생성 중 오류가 발생했어요."}},
        )
