import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Config:
    llm_provider: str  # "gemini" | "azure"

    google_api_key: str
    model_name: str
    embedding_model: str

    azure_api_key: str
    azure_endpoint: str
    azure_api_version: str
    azure_chat_deployment: str
    azure_embedding_deployment: str

    database_url: str

    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str

    top_k: int
    rerank_top_n: int
    confidence_threshold: float
    max_retries: int


_llm_provider = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()

config = Config(
    llm_provider=_llm_provider,
    # 활성 프로바이더가 아닌 쪽의 키는 없어도 되므로, 그 경우엔 필수 검증을 하지 않는다.
    google_api_key=_require_env("GOOGLE_API_KEY") if _llm_provider == "gemini" else os.environ.get("GOOGLE_API_KEY", ""),
    model_name=os.environ.get("MODEL_NAME", "gemini-3.5-flash"),
    embedding_model=os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001"),
    azure_api_key=_require_env("AZURE_API_KEY") if _llm_provider == "azure" else os.environ.get("AZURE_API_KEY", ""),
    azure_endpoint=_require_env("AZURE_ENDPOINT") if _llm_provider == "azure" else os.environ.get("AZURE_ENDPOINT", ""),
    azure_api_version=os.environ.get("AZURE_API_VERSION", "2024-12-01-preview"),
    azure_chat_deployment=os.environ.get("AZURE_CHAT_DEPLOYMENT", "gpt-4.1"),
    azure_embedding_deployment=os.environ.get("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
    database_url=_require_env("DATABASE_URL"),
    qdrant_url=_require_env("QDRANT_URL"),
    qdrant_api_key=_require_env("QDRANT_API_KEY"),
    qdrant_collection=os.environ.get("QDRANT_COLLECTION", "ai_wiki_chunks"),
    top_k=int(os.environ.get("TOP_K", "5")),
    rerank_top_n=int(os.environ.get("RERANK_TOP_N", "3")),
    confidence_threshold=float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7")),
    max_retries=int(os.environ.get("MAX_RETRIES", "3")),
)
