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
Question Analyzer      (질문 의도·키워드 추출)
  │
  ▼
Query Optimizer         (검색 질의 생성, 결정론적/LLM 호출 없음)
  │
  ▼
AI Wiki Retriever       (Qdrant 벡터 검색, approval_status=approved 필터)
  │
  ▼
Document Reranker       (벡터 유사도 70% + 키워드 일치 15% + 최신성 10%)
  │
  ▼
Confidence Checker      ← 검색 점수만으로 판단 (답변 생성 전에 확인)
  │
  ├── confidence ≥ 0.7 ─────────────► Context Builder → Answer Generator → END (최종 답변)
  │
  └── confidence < 0.7
        │
        retry_count += 1
        │
        ├── retry_count ≤ 3 ──► Query Rewriter ──► Question Analyzer (루프)
        │
        └── retry_count > 3 ──► END ("담당자 문의" 고정 안내, 답변 생성 없음)
```

Confidence Checker가 검색 점수만으로 먼저 판단하므로, 재시도로 버려질 답변을 매번 생성하는 낭비 호출이 없음

### 노드별 기술 스택

| 노드 | 기술/방식 | LLM 호출 |
| --- | --- | --- |
| Question Analyzer | Gemini `generate_content` + `response_schema`(구조화 JSON)로 intent/keywords 추출 | O |
| Query Optimizer | 순수 Python 로직(키워드+질문 문자열 결합), 외부 호출 없음 | X |
| AI Wiki Retriever | Gemini `embed_content`(`gemini-embedding-001`)로 임베딩 → Qdrant `query_points`로 코사인 유사도 검색(payload 필터: `approvalStatus`) | O (임베딩만) |
| Document Reranker | 결정론적 가중합 스코어링(벡터 유사도 0.75 + 키워드 일치 0.15 + 최신성 0.10), 외부 호출 없음 | X |
| Confidence Checker | Reranker 점수와 임계치(0.7)를 비교하는 단순 로직 | X |
| Context Builder | 선택된 청크를 컨텍스트 문자열로 포맷팅, 외부 호출 없음 | X |
| Answer Generator | Gemini `generate_content` + `response_schema`, 시스템 프롬프트(`AI Wiki Assistant Agent - System Prompt.md`) 로드 | O |
| Query Rewriter | Gemini `generate_content`, 재시도 차수별로 다른 프롬프트/스키마(Query Rewriting / Multi Query Retrieval / Query Expansion) | O |

**공통 인프라**: 오케스트레이션 `langgraph`(Python `StateGraph`), LLM/임베딩 `google-genai` SDK(429/500/503 대상 지수 백오프 재시도 자체 구현), 벡터 DB `qdrant-client`, 메타데이터 저장 `psycopg2`(PostgreSQL).

### Query Rewriter (재시도 3기법)

confidence 미달 시 재시도 차수에 따라 3차에 따른 기법으로 질문을 개선(항상 최초 질문 기준으로 재작성).

| 차수 | 기법 | 내용 |
| --- | --- | --- |
| 1차 | Query Rewriting | 모호한 표현을 플랫폼 용어로 구체화해 한 문장으로 재작성 |
| 2차 | Multi Query Retrieval | 서로 다른 관점의 질의 3개를 생성, Retriever가 각각 검색 후 결과 병합 |
| 3차 | Query Expansion | 관련 동의어/상위어를 덧붙여 검색 범위 확장 |

3회 모두 confidence 기준(0.7)을 넘지 못하면 `"질문에 해당하는 답변을 찾지 못했습니다. 담당자에게 문의 부탁드립니다."`로 종료함

### 데이터 흐름

`data/*.md` → (공통 템플릿 적용) → `wiki/*.md`(frontmatter 메타데이터 포함) → `scripts/ingest.py`가 헤더 기반
청킹 후 Gemini 임베딩(`gemini-embedding-001`) → Qdrant 컬렉션 `ai_wiki_chunks` + Postgres 테이블 `wiki_documents`에 적재.

## 실행 방법

```bash
cd wiki-assistant-py

# 최초 1회: 가상환경 생성 및 의존성 설치
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# .env.example을 복사해 .env를 만들고 GOOGLE_API_KEY, DATABASE_URL, QDRANT_URL, QDRANT_API_KEY를 채운다

# 문서 적재 (최초 1회, 또는 wiki/*.md 변경 시)
.venv\Scripts\python.exe -m scripts.ingest

# 질문
.venv\Scripts\python.exe -m src.ask "GOOD과 DEFECT의 차이는 무엇인가?"
```

PowerShell 실행 정책 때문에 `Activate.ps1`이 막히면, 활성화 없이 `.venv\Scripts\python.exe`를 직접 호출하면 됩니다.

### 주요 환경변수 (`.env`)

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `MODEL_NAME` | `gemini-3.5-flash` | 답변 생성/질문 분석/재작성에 쓰는 모델 |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | 임베딩 모델 |
| `QDRANT_COLLECTION` | `ai_wiki_chunks` | Qdrant 컬렉션명 |
| `TOP_K` | `5` | Retriever가 가져올 후보 청크 수 |
| `RERANK_TOP_N` | `3` | Reranker가 최종 선택할 청크 수 |
| `CONFIDENCE_THRESHOLD` | `0.7` | 답변 확정 기준 신뢰도 |
| `MAX_RETRIES` | `3` | Query Rewriter 최대 재시도 횟수 |

## API 서버 실행 방법

`wiki-assistant-py/app/`에 기존 그래프(`src/graph.py`)를 그대로 감싼 FastAPI 서버가 있습니다.

```bash
cd wiki-assistant-py
.venv\Scripts\python.exe -m pip install -r requirements.txt   # fastapi 등 포함

# 로컬 실행 (개발용, 코드 변경 시 자동 재시작)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 또는
.venv\Scripts\python.exe -m app.main
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker 실행

```bash
docker build -t ai-wiki-assistant .
docker run -p 8000:8000 --env-file .env ai-wiki-assistant
```

### API

**Health Check**
```
GET /health
→ {"status": "UP"}
```

**채팅**
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
curl http://localhost:8000/health

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user001","question":"GOOD과 DEFECT의 차이는?"}'
```

## 제약사항 / TODO

- **Multi Query Retrieval 순차 처리**: 2차 재시도 시 질의 변형 3개를 순차적으로 임베딩·검색합니다(병렬 처리 아님). 해당 구간에서 지연이 발생할 수 있습니다.
- **Postgres 연결**: 모듈 로드 시 커넥션 하나를 계속 재사용합니다. 장시간 실행 서비스로 만들 경우 커넥션 풀링이 필요합니다.
- **자동 승인**: `scripts/ingest.py`는 데모 목적으로 적재 시 `approval_status`를 자동으로 `approved` 처리합니다(원본 `wiki/*.md`는 `pending` 유지). 실제 운영에는 별도 승인 워크플로가 필요합니다.
- **Gemini 무료 티어 쿼터**: 재시도 루프는 질문 1건당 Gemini 호출이 여러 번(최악의 경우 10회 내외) 발생할 수 있어 무료 티어 쿼터에 걸리기 쉽습니다. 지속 사용 시 유료 플랜을 권장합니다.
- **confidence 신뢰성**: 벡터 유사도 단일 지표만으로 판단하므로, 도메인과 무관한 질문에 관련 용어가 우연히 섞이면 오탐할 수 있습니다(프롬프트 가드로 완화했으나 근본 해결은 아님).
- **API 인증/속도제한 없음**: 현재 CORS `*` 허용, 인증 없이 열려 있습니다. 외부 공개 시 API 키 검증이나 rate limiting 추가가 필요합니다.
- **user_id 미사용**: 요청에서 받지만 로깅에만 쓰고 그래프 상태에는 반영하지 않습니다. 세션별 대화 이력이 필요해지면 `state.py`에 필드 추가가 필요합니다.
- **동시 요청과 쿼터**: 요청 1건당 Gemini 호출이 여러 번 발생하므로, 동시 사용자가 늘면 무료 티어 쿼터에 더 쉽게 걸립니다.

