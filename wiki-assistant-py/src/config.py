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
    google_api_key: str
    model_name: str
    embedding_model: str

    database_url: str

    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str

    top_k: int
    rerank_top_n: int
    confidence_threshold: float
    max_retries: int


config = Config(
    google_api_key=_require_env("GOOGLE_API_KEY"),
    model_name=os.environ.get("MODEL_NAME", "gemini-3.5-flash"),
    embedding_model=os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001"),
    database_url=_require_env("DATABASE_URL"),
    qdrant_url=_require_env("QDRANT_URL"),
    qdrant_api_key=_require_env("QDRANT_API_KEY"),
    qdrant_collection=os.environ.get("QDRANT_COLLECTION", "ai_wiki_chunks"),
    top_k=int(os.environ.get("TOP_K", "5")),
    rerank_top_n=int(os.environ.get("RERANK_TOP_N", "3")),
    confidence_threshold=float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7")),
    max_retries=int(os.environ.get("MAX_RETRIES", "3")),
)
