from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_ERROR_BODY_DEFAULTS = {
    "intent": None,
    "keywords": None,
    "confidence_score": None,
    "retry_count": None,
    "runtime": None,
}


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "answer": str(exc.errors()[0]["msg"]),
            **_ERROR_BODY_DEFAULTS,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "answer": "AI 처리 중 오류가 발생했습니다.",
            **_ERROR_BODY_DEFAULTS,
        },
    )
