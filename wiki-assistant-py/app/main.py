from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, proxy_chat
from app.core import config
from app.core.exception import generic_exception_handler, validation_exception_handler

app = FastAPI(
    title="AI Wiki Assistant",
    description="LangGraph 기반 AI Wiki 어시스턴트 서비스",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
# 경로 자체가 /assistant/v1/chat이라 접두사 없이 등록한다(backend-proxy가 그대로 호출).
app.include_router(proxy_chat.router, tags=["proxy-chat"])


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "UP"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=config.PORT, reload=True)
