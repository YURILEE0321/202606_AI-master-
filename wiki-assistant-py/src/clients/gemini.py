import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar

from google import genai
from google.genai import types
from google.genai.errors import APIError

from ..config import config

_client = genai.Client(api_key=config.google_api_key)

# 429(쿼터)/500/503(일시적 과부하)는 무료 티어에서 흔히 발생하므로 지수 백오프로 재시도한다.
_RETRYABLE_STATUSES = {429, 500, 503}
_MAX_API_RETRIES = 3
_BASE_DELAY_SECONDS = 1.0
_MAX_DELAY_SECONDS = 30.0

T = TypeVar("T")


def _suggested_delay_seconds(err: APIError) -> Optional[float]:
    # 429 응답에는 서버가 권장하는 재시도 대기시간(RetryInfo.retryDelay, 예: "16s")이 담겨 있다.
    # 무료 티어의 분당 쿼터는 고정 백오프(1s/2s/4s)보다 훨씬 길게 기다려야 풀리는 경우가 많아,
    # 있으면 그 값을 우선 사용한다.
    try:
        details = err.details or {}
        error_obj = details.get("error", details) if isinstance(details, dict) else {}
        for d in error_obj.get("details", []):
            if str(d.get("@type", "")).endswith("RetryInfo"):
                match = re.match(r"([\d.]+)s", str(d.get("retryDelay", "")))
                if match:
                    return float(match.group(1))
    except Exception:
        pass
    return None


def _with_retry(label: str, fn: Callable[[], T]) -> T:
    attempt = 0
    while True:
        try:
            return fn()
        except APIError as err:
            status = err.code
            if status not in _RETRYABLE_STATUSES or attempt >= _MAX_API_RETRIES:
                raise
            delay = _suggested_delay_seconds(err) or (_BASE_DELAY_SECONDS * (2**attempt))
            delay = min(delay, _MAX_DELAY_SECONDS)
            print(f"[gemini] {label} status={status} -> {delay:.0f}s 후 재시도 ({attempt + 1}/{_MAX_API_RETRIES})")
            time.sleep(delay)
            attempt += 1


_GEMINI_TYPE_MAP = {
    "object": types.Type.OBJECT,
    "string": types.Type.STRING,
    "array": types.Type.ARRAY,
    "number": types.Type.NUMBER,
    "integer": types.Type.INTEGER,
    "boolean": types.Type.BOOLEAN,
}


def _to_gemini_schema(schema: Any) -> Any:
    # 노드는 프로바이더 중립적인 JSON Schema(소문자 type 문자열)로 스키마를 정의한다.
    # Gemini SDK는 types.Type enum을 요구하므로 여기서 변환한다.
    if not isinstance(schema, dict):
        return schema
    result: Dict[str, Any] = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            result[key] = _GEMINI_TYPE_MAP.get(value, value)
        elif key == "properties" and isinstance(value, dict):
            result[key] = {k: _to_gemini_schema(v) for k, v in value.items()}
        elif key == "items":
            result[key] = _to_gemini_schema(value)
        elif key == "additionalProperties":
            continue  # Gemini Schema에는 없는 필드라 제거한다.
        else:
            result[key] = value
    return result


def embed_texts(texts: List[str]) -> List[List[float]]:
    def _call():
        return _client.models.embed_content(model=config.embedding_model, contents=texts)

    response = _with_retry("embed_content", _call)
    embeddings = response.embeddings
    if not embeddings or len(embeddings) != len(texts):
        raise RuntimeError("Gemini embed_content returned an unexpected number of embeddings")
    return [e.values for e in embeddings]


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]


def generate_json(prompt: str, schema: Dict[str, Any], system_instruction: Optional[str] = None) -> Any:
    def _call():
        return _client.models.generate_content(
            model=config.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=_to_gemini_schema(schema),
            ),
        )

    response = _with_retry("generate_content", _call)
    text = response.text
    if not text:
        raise RuntimeError("Gemini generate_content returned an empty response")
    return json.loads(text)
