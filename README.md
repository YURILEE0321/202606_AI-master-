# AI Wiki Assistant

AI Defect Inspection / AI 비전 검사 플랫폼의 시스템 매뉴얼·용어사전·메뉴 가이드를 Wiki 형태로 정리하고,
RAG(LangGraph) 기반으로 자연어 질문에 답하는 AI Wiki Assistant 프로젝트

## 리포지토리 구조

```
data/              원본 문서(사용자 매뉴얼, 용어 사전, 메뉴 사용법)
wiki/              data/를 공통 템플릿 + 메타데이터(frontmatter)로 변환한 Wiki 문서
개발환경/           개발 환경 설정 값, Agent 시스템 프롬프트
시나리오/           문제 정의, 시나리오, 상세 설계 문서
wiki-assistant-py/ AI Wiki Assistant의 LangGraph 파이프라인 구현 (Python, 유지보수 대상)
```

## wiki-assistant-py — LangGraph 파이프라인

### 플로우

```
START
  │
  ▼
Conversation History (최근 5턴)   ← history[-(5*2):], 1턴 = 사용자+어시스턴트 한 쌍
  │
  ▼
Question Analyzer      (Intent Classification + Entity Extraction + Keyword Extraction)
  │
  ▼
Query Optimizer         (검색 질의 생성, 결정론적/LLM 호출 없음)
  │
  ▼
AI Wiki Retriever       (Qdrant 벡터 검색, approval_status=approved 필터)
  │
  ▼
Document Reranker       (벡터 유사도 65% + 개체명 일치 15% + 키워드 일치 10% + 최신성 10%)
  │
  ▼
Context Builder         (컨텍스트 문자열 조립, LLM 호출 없음 — Confidence Checker가 RAGAS 평가에 필요)
  │
  ▼
Confidence Checker      ← Similarity Score + RAGAS(Context Precision/Recall) 가중 평균 (답변 생성 전에 확인)
  │
  ├── confidence ≥ 0.7 ─────────────► Answer Generator → END (최종 답변, Faithfulness/Answer Relevancy 참고 평가)
  │
  └── confidence < 0.7
        │
        retry_count += 1
        │
        ├── retry_count ≤ 3 ──► Query Rewriter ──► Question Analyzer (루프)
        │
        └── retry_count > 3 ──► END ("담당자 문의" 고정 안내, 답변 생성 없음)
```

Context Builder는 LLM 호출이 없어 항상 먼저 실행해도 비용이 없고, Confidence Checker가 그 컨텍스트로 RAGAS 사전 지표까지 평가한 뒤 통과할 때만 Answer Generator(LLM)를 호출하므로, 재시도로 버려질 답변을 매번 생성하는 낭비 호출이 없음

### 노드별 기술 스택

| 노드 | 기술/방식 | LLM 호출 |
| --- | --- | --- |
| Question Analyzer | `generate_json` + 구조화 JSON 스키마로 intent/entities/keywords 추출 | O |
| Query Optimizer | 순수 Python 로직(entities를 2배 가중해 keywords+질문과 결합), 외부 호출 없음 | X |
| AI Wiki Retriever | `embed_text`로 임베딩 → Qdrant `query_points`로 코사인 유사도 검색(payload 필터: `approvalStatus`) | O (임베딩만) |
| Document Reranker | 결정론적 가중합 스코어링(벡터 유사도 0.65 + 개체명 일치 0.15 + 키워드 일치 0.10 + 최신성 0.10), 외부 호출 없음 | X |
| Context Builder | 선택된 청크를 컨텍스트 문자열로 포맷팅, 외부 호출 없음 | X |
| Confidence Checker | Similarity Score + RAGAS(Context Precision/Recall, `generate_json` 1회) 가중 평균을 임계치(0.7)와 비교 | O |
| Answer Generator | `generate_json`로 답변 생성 + RAGAS(Faithfulness/Answer Relevancy, `generate_json` 1회, 참고용) 평가 | O |
| Query Rewriter | `generate_json`, 재시도 차수별로 다른 프롬프트/스키마(Query Rewriting / Multi Query Retrieval / Query Expansion) | O |

`generate_json`/`embed_text`는 `src/clients/llm.py`가 노출하는 프로바이더 중립 함수로, 노드는 어떤 LLM을 쓰는지 몰라도 된다(아래 "LLM 프로바이더 전환" 참고).

**Entity vs Keyword**: `entities`는 질문에 명시적으로 등장하는 구체적 고유명사만(메뉴명, GOOD/DEFECT 같은 용어, 시스템/설비명, 코드/ID 등) — `keywords`보다 좁고 정확한 검색 앵커다. `keywords`는 동의어·관련어를 포함할 수 있는 더 넓은 범위. Query Optimizer는 `entities`를 검색 질의에서 2배 가중하고, Document Reranker도 개체명 일치를 키워드 일치보다 높게(0.15 vs 0.10) 반영한다.

**공통 인프라**: 오케스트레이션 `langgraph`(Python `StateGraph`), 벡터 DB `qdrant-client`, 메타데이터 저장 `psycopg2`(PostgreSQL), LLM/임베딩은 `LLM_PROVIDER`에 따라 `google-genai` 또는 `openai`(Azure) SDK(둘 다 429/500/503 대상 지수 백오프 재시도 자체 구현).

### Confidence Checker (Similarity + RAGAS)

`confidence_score`(Final Score)는 두 신호의 가중 평균이다(`src/nodes/confidence_checker.py`).

| 신호 | 가중치 | 설명 |
| --- | --- | --- |
| Similarity Score | 0.4 | Document Reranker가 낸 top-1 청크의 벡터 유사도 |
| RAGAS 사전 지표 | 0.6 | `(Context Precision + Context Recall) / 2` — LLM이 검색된 컨텍스트만 보고 평가(정답 레퍼런스 없음) |

RAGAS 쪽에 더 높은 가중치를 준 이유: Similarity Score는 top-1 청크 하나의 벡터 유사도뿐이라 "그럴듯하지만 실제로는 무관한" 검색에 취약하다(과거 도메인 무관 질문에서 실제로 겪은 문제). Context Recall은 검색된 문서 **전체**가 질문에 답하기 충분한 정보를 담고 있는지까지 LLM이 직접 판단해 Similarity Score가 못 보는 실패 모드를 잡아준다. 다만 Similarity Score도 추가 비용 없이 이미 계산돼 있고 LLM 판단의 노이즈를 보정하는 역할을 하므로 완전히 배제하지 않았다.

**Faithfulness / Answer Relevancy(참고용)**: 이 둘은 "생성된 답변"이 있어야 계산 가능해서 Answer Generator가 답변을 만든 **뒤** 평가한다. 이미 Confidence Checker가 통과 판정을 내린 다음이라 재시도를 다시 트리거하지는 않고, 로그와 API 응답에 참고 지표로만 남긴다. `ragas_full_score = (context_precision + context_recall + faithfulness + answer_relevancy) / 4`로 4개 지표를 25%씩 반영해 계산한다.

**RAGAS 패키지 대신 자체 구현한 이유**: 실제 `ragas` 패키지의 Context Recall은 정답 레퍼런스(ground truth)가 있어야 계산되는데, 이 프로젝트는 라이브 사용자 질문을 다루므로 정답 레퍼런스가 없다. 그래서 `src/lib/ragas_metrics.py`에서 기존 `generate_json`(프로바이더 중립)으로 레퍼런스 없이(reference-free) LLM이 직접 심사하도록 구현했다.

### LLM 프로바이더 전환 (Gemini ↔ Azure OpenAI)

`.env`의 `LLM_PROVIDER`(`gemini` | `azure`)로 전환한다. 노드 코드는 전혀 건드릴 필요 없이 `src/clients/llm.py`가 아래 둘 중 하나를 골라 노출한다.

| 프로바이더 | 클라이언트 | 채팅 모델 | 임베딩 모델 |
| --- | --- | --- | --- |
| `gemini` | `src/clients/gemini.py` (`google-genai` SDK) | `MODEL_NAME`(예: `gemini-3.5-flash`) | `EMBEDDING_MODEL`(예: `gemini-embedding-001`) |
| `azure` | `src/clients/azure_openai.py` (`openai` SDK의 `AzureOpenAI`) | `AZURE_CHAT_DEPLOYMENT`(예: `gpt-4.1`) | `AZURE_EMBEDDING_DEPLOYMENT`(예: `text-embedding-3-large`) |

구조화 출력 스키마는 노드에서 `{"type": "object", ...}`처럼 소문자 JSON Schema로 한 번만 정의하고, 각 클라이언트가 내부에서 자기 SDK 형식으로 변환한다(Gemini는 `types.Type` enum, Azure는 Structured Outputs strict 모드용 `additionalProperties: false` 보강).

⚠️ **전환 시 반드시 재적재 필요**: Gemini와 OpenAI 임베딩은 서로 다른 벡터 공간이라, 프로바이더를 바꾸면 `scripts/ingest.py`를 다시 실행해 Qdrant에 새 임베딩으로 재적재해야 검색이 정상 동작한다(두 모델 모두 기본 출력 차원이 3072라 컬렉션 재생성은 필요 없음).

### Query Rewriter (재시도 3기법)

confidence 미달 시 재시도 차수에 따라 3차에 따른 기법으로 질문을 개선(항상 최초 질문 기준으로 재작성).

| 차수 | 기법 | 내용 |
| --- | --- | --- |
| 1차 | Query Rewriting | 모호한 표현을 플랫폼 용어로 구체화해 한 문장으로 재작성(entities 표현을 최대한 유지) |
| 2차 | Query Expansion | 관련 동의어/상위어를 덧붙여 검색 범위 확장 |
| 3차 | Multi Query Retrieval | 서로 다른 관점의 질의 3개를 생성, Retriever가 각각 검색 후 결과 병합 |

3회 모두 confidence 기준(0.7)을 넘지 못하면 `"질문에 해당하는 답변을 찾지 못했습니다. 담당자에게 문의 부탁드립니다."`로 종료함

### 멀티턴 대화 (Window Memory)

`/assistant/v1/chat`(②번 API)는 요청마다 `history`(해당 space의 전체 대화 기록)를 함께 받는다. 대화가
10턴 가까이 길어져도 프롬프트에 넣는 맥락 크기가 계속 늘어나지 않도록, Question Analyzer 진입 직전에
**최근 N턴(기본 5턴, window memory)만 잘라** 사용한다.

```
사용자 질문
  │
  ▼
Conversation History (최근 5턴)   ← history[-(5*2):], 1턴 = 사용자+어시스턴트 한 쌍
  │
  ▼
Question Analyzer      (지시어/생략된 주어를 대화 맥락에서 해석해 entities/keywords에 반영)
  │
  ▼
Query Optimizer → AI Wiki Retriever → ... (이후 플로우는 기존과 동일)
```

**예시**

```
Q1. Review 메뉴가 뭐야?
A1. AI 결과를 검토하는 화면입니다.

Q2. 그럼 여기서 배포도 가능해?
```

Q2만 보면 "여기서"가 무엇을 가리키는지 알 수 없지만, Question Analyzer가 직전 대화(Q1/A1)를 함께
받아 "여기서" → `Review 메뉴`로 해석하고 `entities: ["Review 메뉴"]`, `keywords: ["Review 메뉴", "배포", ...]`로
추출한다. 이전 대화와 무관하거나 지시 대상이 불명확하면 추측해서 채우지 않도록 프롬프트에 명시했다
(`src/prompts.py::QUESTION_ANALYZER_PROMPT`).

- Window 자르기: `src/nodes/question_analyzer.py::_recent_turns` — `history[-(HISTORY_WINDOW_TURNS*2):]`
- 대화 맥락 프롬프트 조립: `src/prompts.py::build_question_analyzer_prompt`
- `history` 자체는 잘리지 않고 요청 원본 그대로 상태에 저장되며(로그/추후 확장용), Question Analyzer가
  쓸 때만 윈도우를 적용한다 — 즉 대화 저장은 backend-proxy(`chat_messages` 테이블)가 계속 전체를 갖고
  있고, 우리 쪽에서 매 요청마다 "최근 5턴만 본다"는 정책만 적용하는 구조다.

### 데이터 흐름

`data/*.md` → (공통 템플릿 적용) → `wiki/*.md`(frontmatter 메타데이터 포함) → `scripts/ingest.py`가 헤더 기반
청킹 후 임베딩(`LLM_PROVIDER`에 따라 Gemini 또는 Azure OpenAI) → Qdrant 컬렉션 `ai_wiki_chunks` + Postgres 테이블 `wiki_documents`에 적재.

## 실행 방법

```bash
cd wiki-assistant-py

# 최초 1회: 가상환경 생성 및 의존성 설치
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# .env를 만들고 아래 "주요 환경변수" 표를 참고해 값을 채운다
# (DATABASE_URL, QDRANT_URL, QDRANT_API_KEY는 공통 필수. LLM_PROVIDER에 따라 GOOGLE_API_KEY 또는 AZURE_* 필요)

# 문서 적재 (최초 1회, 또는 wiki/*.md 변경 시)
.venv\Scripts\python.exe -m scripts.ingest

# 질문
.venv\Scripts\python.exe -m src.ask "GOOD과 DEFECT의 차이는 무엇인가?"
```

PowerShell 실행 정책 때문에 `Activate.ps1`이 막히면, 활성화 없이 `.venv\Scripts\python.exe`를 직접 호출하면 됩니다.

### 주요 환경변수 (`.env`)

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `LLM_PROVIDER` | `gemini` | `gemini` 또는 `azure` |
| `GOOGLE_API_KEY` | (필수, `gemini`일 때) | Gemini API 키 |
| `MODEL_NAME` | `gemini-3.5-flash` | Gemini 채팅 모델 |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini 임베딩 모델 |
| `AZURE_API_KEY` | (필수, `azure`일 때) | Azure OpenAI API 키 |
| `AZURE_ENDPOINT` | (필수, `azure`일 때) | Azure OpenAI 리소스 endpoint (예: `https://<리소스>.openai.azure.com/`) |
| `AZURE_API_VERSION` | `2024-12-01-preview` | Azure OpenAI API 버전 |
| `AZURE_CHAT_DEPLOYMENT` | `gpt-4.1` | 채팅용 배포 이름 |
| `AZURE_EMBEDDING_DEPLOYMENT` | `text-embedding-3-large` | 임베딩용 배포 이름 |
| `QDRANT_COLLECTION` | `ai_wiki_chunks` | Qdrant 컬렉션명 |
| `TOP_K` | `5` | Retriever가 가져올 후보 청크 수 |
| `RERANK_TOP_N` | `3` | Reranker가 최종 선택할 청크 수 |
| `CONFIDENCE_THRESHOLD` | `0.7` | 답변 확정 기준 신뢰도 |
| `MAX_RETRIES` | `3` | Query Rewriter 최대 재시도 횟수 |
| `HISTORY_WINDOW_TURNS` | `5` | Question Analyzer가 참고할 최근 대화 턴 수(1턴 = 사용자+어시스턴트 한 쌍, window memory) |
| `PORT` | `8001` | FastAPI 서버 포트 |
| `PROXY_DATABASE_URL` | (없으면 `/assistant/v1/chat` 비활성) | 2026_aimaster_wikigen backend-proxy의 Postgres(`wikidb` 스키마) |
| `PROXY_QDRANT_SUMMARY_COLLECTION` / `PROXY_QDRANT_CHUNK_COLLECTION` | `wiki_summary` / `wiki_chunk` | 실제 Builder가 적재한 Qdrant 컬렉션명 (같은 클러스터, 다른 컬렉션) |
| `PROXY_EMBEDDING_MODEL` | `aitl-prd-text-embedding-3-small` | 그 컬렉션이 이미 임베딩된 모델(검색 시에만 사용, 1536차원) |

## API 서버 실행 방법

`wiki-assistant-py/app/`에 기존 그래프(`src/graph.py`)를 그대로 감싼 FastAPI 서버가 있습니다. 엔드포인트가 두 개인데, 그래프/노드 로직은 완전히 동일하고 `wiki_retriever.py`가 `space_id` 유무로 검색 대상만 분기합니다.

```bash
cd wiki-assistant-py
.venv\Scripts\python.exe -m pip install -r requirements.txt   # fastapi 등 포함

# 로컬 실행 (개발용, 코드 변경 시 자동 재시작)
# 8001: 2026_aimaster_wikigen의 backend-proxy가 기본으로 보는 ASSISTANT_API_BASE_URL(127.0.0.1:8001)과 맞춤
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 또는 (.env의 PORT 값 사용)
.venv\Scripts\python.exe -m app.main
```

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Docker 실행

```bash
docker build -t ai-wiki-assistant .
docker run -p 8001:8001 --env-file .env ai-wiki-assistant
```

### API

**Health Check**
```
GET /health
→ {"status": "UP"}
```

**① 자체 채팅 API** — 우리 자체 Qdrant 컬렉션(`ai_wiki_chunks`)을 검색합니다.
```
POST /api/v1/chat
Content-Type: application/json
```

Request:
```json
{ "user_id": "user001", "question": "GOOD과 DEFECT의 차이는?" }
```

Response:
```json
{
  "status": "success",
  "intent": "용어",
  "keywords": ["GOOD", "DEFECT", "차이"],
  "answer": "...",
  "confidence_score": 0.82,
  "retry_count": 0,
  "runtime": 1.204
}
```

오류 시:
```json
{
  "status": "error",
  "intent": null,
  "keywords": null,
  "answer": "AI 처리 중 오류가 발생했습니다.",
  "confidence_score": null,
  "retry_count": null,
  "runtime": null
}
```

curl 예제:
```bash
curl http://localhost:8001/health

curl -X POST http://localhost:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user001","question":"GOOD과 DEFECT의 차이는?"}'
```

**② 2026_aimaster_wikigen 연동 API** — backend-proxy가 그대로 호출하는 엔드포인트(`assistant` 서비스 대체). `space_id`로 backend-proxy Postgres(`wikidb` 스키마)에서 승인된 문서를 조회하고, 실제 Builder가 적재한 Qdrant(`wiki_summary`/`wiki_chunk`)를 검색합니다. `PROXY_DATABASE_URL`이 설정돼 있어야 동작합니다.
```
POST /assistant/v1/chat
Content-Type: application/json
```

Request:
```json
{ "space_id": "spc_7f7008d2e8", "question": "What is bucketing?", "history": [] }
```

`history`에 이전 대화(`{"role": "user"|"assistant", "text": "..."}` 배열)를 넣으면 후속 질문의 지시어
("그거", "여기서" 등)를 이전 맥락에서 해석한다(최근 5턴만 사용, 위 "멀티턴 대화" 절 참고):
```json
{
  "space_id": "spc_7d13c88d88",
  "question": "그거 Primary Key랑 뭐가 달라?",
  "history": [
    { "role": "user", "text": "unique key가 뭐야?" },
    { "role": "assistant", "text": "동일한 UNIQUE KEY를 가진 레코드가 적재되면 새 레코드가 기존 레코드를 덮어쓰는 테이블 유형입니다." }
  ]
}
```

Response:
```json
{
  "answer": "Bucketing은 데이터를 여러 물리적 단위(버킷)로 분산 저장하여...",
  "sources": [
    { "document_id": "doc_5d43d64002", "title": "Bucketing", "score": 0.44 }
  ]
}
```
승인된 문서가 없는 space면 `{"answer": "관련된 승인 문서를 찾지 못했어요.", "sources": []}`를 그래프 실행 없이 즉시 반환합니다.

curl 예제:
```bash
curl -X POST http://localhost:8001/assistant/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"space_id":"spc_7f7008d2e8","question":"What is bucketing?","history":[]}'
```


