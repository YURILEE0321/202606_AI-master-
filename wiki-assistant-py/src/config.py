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
    # backend-proxy(2026_aimaster_wikigen)가 쓰는 Postgres. space_id -> 승인된 wiki_doc_id 조회 전용(읽기만).
    # 비어있으면 /assistant/v1/chat 라우트가 비활성화된다(app/services/proxy_chat_service.py에서 검사).
    proxy_database_url: str
    # Neon 풀링 커넥션은 접속 문자열의 search_path 옵션을 지원하지 않아 접속 직후 SET으로 처리해야 한다
    # (예: "wikidb,public"). 원본 assistant 배포에서는 DB 역할(role)의 기본 search_path가 이미 맞게
    # 설정돼 있어 필요 없었지만, 우리 공유 Neon에서는 필요하다. 비어있으면 아무것도 하지 않는다.
    proxy_db_search_path: str

    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str

    top_k: int
    rerank_top_n: int
    confidence_threshold: float
    max_retries: int

    # 2026_aimaster_wikigen의 실제 Builder가 이미 적재해둔 컬렉션/임베딩 모델(우리 자체 컬렉션과 별개).
    # 같은 Qdrant 클러스터(qdrant_url/qdrant_api_key)에 있지만 컬렉션명이 다르다.
    proxy_qdrant_summary_collection: str
    proxy_qdrant_chunk_collection: str
    proxy_embedding_model: str
    proxy_top_k_summary: int
    proxy_top_k_chunk: int

    # 멀티턴 대화(window memory): Question Analyzer에 넘길 최근 대화 턴 수(1턴 = 사용자+어시스턴트 한 쌍).
    # 전체 대화가 이보다 길어도(예: 10턴) 프롬프트에는 최근 N턴만 사용해 토큰/노이즈를 억제한다.
    history_window_turns: int


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
    proxy_database_url=os.environ.get("PROXY_DATABASE_URL", ""),
    proxy_db_search_path=os.environ.get("PROXY_DB_SEARCH_PATH", ""),
    qdrant_url=_require_env("QDRANT_URL"),
    qdrant_api_key=_require_env("QDRANT_API_KEY"),
    qdrant_collection=os.environ.get("QDRANT_COLLECTION", "ai_wiki_chunks"),
    top_k=int(os.environ.get("TOP_K", "5")),
    rerank_top_n=int(os.environ.get("RERANK_TOP_N", "3")),
    confidence_threshold=float(os.environ.get("CONFIDENCE_THRESHOLD", "0.7")),
    max_retries=int(os.environ.get("MAX_RETRIES", "3")),
    proxy_qdrant_summary_collection=os.environ.get("PROXY_QDRANT_SUMMARY_COLLECTION", "wiki_summary"),
    proxy_qdrant_chunk_collection=os.environ.get("PROXY_QDRANT_CHUNK_COLLECTION", "wiki_chunk"),
    proxy_embedding_model=os.environ.get("PROXY_EMBEDDING_MODEL", "aitl-prd-text-embedding-3-small"),
    proxy_top_k_summary=int(os.environ.get("PROXY_TOP_K_SUMMARY", "5")),
    proxy_top_k_chunk=int(os.environ.get("PROXY_TOP_K_CHUNK", "8")),
    history_window_turns=int(os.environ.get("HISTORY_WINDOW_TURNS", "5")),
)
