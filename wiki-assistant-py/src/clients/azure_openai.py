import json
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

from openai import APIError, AzureOpenAI

from ..config import config

_client = AzureOpenAI(
    api_key=config.azure_api_key,
    azure_endpoint=config.azure_endpoint,
    api_version=config.azure_api_version,
)

# 429(쿼터)/500/503(일시적 과부하)는 흔히 발생하므로 지수 백오프로 재시도한다.
_RETRYABLE_STATUSES = {429, 500, 503}
_MAX_API_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0
_MAX_DELAY_SECONDS = 30.0

T = TypeVar("T")


def _suggested_delay_seconds(err: APIError) -> Optional[float]:
    # 429 응답에는 서버가 권장하는 Retry-After 헤더가 담겨 있는 경우가 많다.
    try:
        headers = getattr(getattr(err, "response", None), "headers", None)
        if headers and "retry-after" in headers:
            return float(headers["retry-after"])
    except Exception:
        pass
    return None


def _with_retry(label: str, fn: Callable[[], T]) -> T:
    attempt = 0
    while True:
        try:
            return fn()
        except APIError as err:
            status = getattr(err, "status_code", None) or getattr(err, "code", None)
            if status not in _RETRYABLE_STATUSES or attempt >= _MAX_API_RETRIES:
                raise
            delay = _suggested_delay_seconds(err) or (_BASE_DELAY_SECONDS * (2**attempt))
            delay = min(delay, _MAX_DELAY_SECONDS)
            print(f"[azure] {label} status={status} -> {delay:.0f}s 후 재시도 ({attempt + 1}/{_MAX_API_RETRIES})")
            time.sleep(delay)
            attempt += 1


def embed_texts(texts: List[str]) -> List[List[float]]:
    def _call():
        return _client.embeddings.create(model=config.azure_embedding_deployment, input=texts)

    response = _with_retry("embeddings.create", _call)
    return [d.embedding for d in response.data]


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]


def _to_strict_schema(schema: Any) -> Any:
    # Azure OpenAI의 Structured Outputs(strict 모드)는 object 타입마다
    # additionalProperties: false를 요구한다. 노드가 정의한 스키마는 그대로 두고 여기서 보강한다.
    if not isinstance(schema, dict):
        return schema
    result = dict(schema)
    if result.get("type") == "object":
        result.setdefault("additionalProperties", False)
        if "properties" in result:
            result["properties"] = {k: _to_strict_schema(v) for k, v in result["properties"].items()}
    if "items" in result:
        result["items"] = _to_strict_schema(result["items"])
    return result


def generate_json(prompt: str, schema: Dict[str, Any], system_instruction: Optional[str] = None) -> Any:
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    def _call():
        return _client.chat.completions.create(
            model=config.azure_chat_deployment,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": _to_strict_schema(schema),
                    "strict": True,
                },
            },
        )

    response = _with_retry("chat.completions.create", _call)
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("Azure OpenAI chat.completions returned an empty response")
    return json.loads(text)
