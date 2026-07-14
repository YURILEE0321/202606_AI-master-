# 2026_aimaster_wikigen 데이터를 검색할 때만 쓰는 임베딩 클라이언트.
# wiki_summary/wiki_chunk가 aitl-prd-text-embedding-3-small(1536차원)로 이미 임베딩되어 있어서,
# 우리 LLM_PROVIDER(gemini/azure) 설정과 무관하게 이 모델로만 쿼리를 임베딩해야 벡터 차원이 맞는다.
# 같은 Azure OpenAI 리소스(azure_endpoint)에 이 배포가 함께 있어 별도 자격증명 없이 재사용한다.
from typing import List

from openai import AzureOpenAI

from ..config import config

_client = AzureOpenAI(
    api_key=config.azure_api_key,
    azure_endpoint=config.azure_endpoint,
    api_version=config.azure_api_version,
)


def embed_text_aitl(text: str) -> List[float]:
    response = _client.embeddings.create(model=config.proxy_embedding_model, input=text)
    return response.data[0].embedding
