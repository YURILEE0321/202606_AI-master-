# LLM_PROVIDER 환경변수에 따라 Gemini/Azure OpenAI 클라이언트 중 하나를 노출한다.
# 노드는 이 모듈에서만 import하면 되고, 프로바이더별 구체 구현(Type 표현, SDK 등)은 몰라도 된다.
# 스키마는 항상 소문자 JSON Schema 스타일("object"/"string"/"array")로 정의한다.
from ..config import config

if config.llm_provider == "azure":
    from .azure_openai import embed_text, embed_texts, generate_json
elif config.llm_provider == "gemini":
    from .gemini import embed_text, embed_texts, generate_json
else:
    raise RuntimeError(
        f"Unknown LLM_PROVIDER: {config.llm_provider!r} (must be 'gemini' or 'azure')"
    )

__all__ = ["embed_text", "embed_texts", "generate_json"]
