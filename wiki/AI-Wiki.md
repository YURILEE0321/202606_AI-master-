---
wiki_id: AI-WIKI-001
title: AI Defect Inspection Platform / AI 비전 검사 시스템 통합 Wiki
version: v1.0
created_date: 2026-07-02
approval_status: pending
document_count: 3
---

# AI Defect Inspection Platform 통합 Wiki

`data/` 폴더의 원본 문서 3건을 [공통 템플릿](_template.md)에 맞춰 변환하고 메타데이터를 부여한 뒤 하나로 통합한 AI Wiki이다.
AI Wiki Assistant는 본 문서를 승인(approval_status: approved)된 이후부터 RAG 검색 근거로 사용한다.

## 목차 및 문서 메타데이터

| No | 문서 ID | 제목 | 유형 | 카테고리 | 승인 상태 | 원본 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MANUAL-021 | AI 비전 검사 시스템 사용자 매뉴얼 | 사용자 매뉴얼 | AI 비전 검사 시스템 | pending | `data/21 시스템 사용자 매뉴얼.md` |
| 2 | GLOSSARY-022 | AI Defect Inspection Platform 용어 사전 | 용어 사전 | AI Defect Inspection Platform | pending | `data/22 용어 사전.md` |
| 3 | MENU-001 | AI Defect Inspection Platform 메뉴 사용법 | 메뉴 가이드 | AI Defect Inspection Platform | pending | `data/메뉴 사용법.md` |

---

# 1. MANUAL-021 · AI 비전 검사 시스템 사용자 매뉴얼

> doc_type: 사용자 매뉴얼 · category: AI 비전 검사 시스템 · version: v1.0 · created_date: 2026-07-02 · approval_status: pending · tags: [비전검사, GOOD, DEFECT, 리뷰, AI모델, 설비관리, 신뢰도] · related_menus: [설비관리, 이미지 조회, AI 평가, 리뷰, 모델관리]

## 개요

AI 비전 검사 시스템은 생산 설비에서 촬영한 제품 이미지를 AI 모델이 자동으로 분석하여 양품(GOOD)과 불량(DEFECT)을 판정하는 시스템이다.
판정 결과는 운영자가 검토(Review)하여 최종 결과를 확정하며, 확정된 결과는 품질 관리 및 AI 모델 성능 개선에 활용된다.

## 예상 질문

- "GOOD과 DEFECT의 차이는 무엇인가?"
- "리뷰는 언제 수행하는가?"
- "신뢰도가 낮으면 어떻게 처리하는가?"
- "AI 모델은 여러 버전을 사용할 수 있는가?"
- "설비에서 이미지가 들어오면 어떤 절차로 처리되는가?"
- "최종 판정은 누가 결정하는가?"
- "DEFECT 판정 기준에는 어떤 항목이 있는가?"

## 주요 내용

### 업무 흐름

```
생산 설비 → 이미지 촬영 → AI 모델 자동 판정 → 운영자 검토(Review) → 최종 판정 완료
```

### 시스템 구성

| 메뉴 | 설명 |
| --- | --- |
| 설비관리 | 설비 정보 조회 |
| 이미지 조회 | 설비에서 유입된 이미지 조회 |
| AI 평가 | AI 모델의 판정 결과 조회 |
| 리뷰 | 운영자가 최종 결과 검토 |
| 모델관리 | AI 모델 정보 관리 |

### 설비관리

설비관리에서는 생산 설비 정보를 조회한다.

조회 항목: 설비코드, 설비명, 설비종류, 설치위치, 사용여부

| 설비코드 | 설비명 | 위치 |
| --- | --- | --- |
| EQ001 | Vision Line 1 | A동 |
| EQ002 | Vision Line 2 | A동 |
| EQ003 | Final Inspection | B동 |

### 이미지 데이터 조회

설비에서 촬영된 이미지 정보를 조회한다.

조회 조건: LOT 번호, 설비, 유입일시, 판정결과

| 항목 | 설명 |
| --- | --- |
| LOT 번호 | 생산 LOT |
| 설비 | 이미지 생성 설비 |
| 유입일시 | 이미지 생성 시각 |
| 이미지 | 원본 이미지 |
| AI 판정 | GOOD / DEFECT |

### AI 모델 평가

이미지마다 AI 모델이 자동으로 판정을 수행한다.

평가 절차: 이미지 수신 → AI 모델 추론 → 신뢰도 계산 → 판정 저장

| 결과 | 의미 |
| --- | --- |
| GOOD | 양품 |
| DEFECT | 불량 |

**신뢰도(Confidence)**: AI가 예측한 확률이다.

```
GOOD
Confidence : 98.45%
```

신뢰도가 낮은 경우 운영자의 검토가 필요하다.

### 리뷰(Review)

운영자는 AI 판정을 확인하고 최종 결과를 확정한다.

리뷰 절차: AI 판정 확인 → 이미지 확인 → 코멘트 입력 → 최종 판정 → 검토 완료

| 항목 | 설명 |
| --- | --- |
| 리뷰어 | 검토자 |
| 코멘트 | 검토 의견 |
| 최종판정 | GOOD / DEFECT |
| 검토일시 | 검토 완료시간 |

예시
```
리뷰어 : 홍길동
코멘트 : Scratch가 미세하여 양품으로 변경
최종판정 : GOOD
```

### AI 모델 관리

시스템에서는 여러 버전의 AI 모델을 관리할 수 있다.

조회 항목: 모델명, 버전, 배포일, 사용여부

| 모델명 | 버전 |
| --- | --- |
| Vision Detector | v1.0 |
| Vision Detector | v1.1 |
| Vision Detector | v2.0 |

최신 모델만 운영에 사용된다.

### 판정 기준

**GOOD** — 다음 조건을 모두 만족하면 양품으로 판정한다.
- Scratch 없음 / Crack 없음 / Chip 없음 / Contamination 없음

**DEFECT** — 다음 중 하나라도 존재하면 불량으로 판정한다.
- Scratch / Crack / Chip / Foreign Material / Stain / Contamination

### 업무 시나리오

**시나리오 1**: 생산 LOT가 완료되면 설비가 이미지를 촬영한다. AI가 자동으로 양품 여부를 판정한다. 운영자는 판정 결과를 검토한 후 최종 결과를 확정한다.

**시나리오 2**: 운영자는 DEFECT 결과만 조회한다. 신뢰도가 90% 이하인 이미지부터 검토한다. 최종 판정을 변경하면 리뷰 이력이 저장된다.

## 관련 용어

| 용어 | 설명 |
| --- | --- |
| LOT | 동일 생산 단위 |
| AI Model | 이미지 판정 모델 |
| Confidence | AI 예측 신뢰도 |
| GOOD | 양품 |
| DEFECT | 불량 |
| Review | 운영자의 최종 검토 |
| Equipment | 생산 설비 |

## 관련 메뉴 / 업무 절차

설비관리 → 이미지 조회 → AI 평가 → 리뷰 → 모델관리 순으로 데이터가 조회·처리된다.

## FAQ

**Q. AI가 GOOD으로 판정했는데 실제는 불량입니다.**
A. 리뷰 메뉴에서 최종 판정을 변경하면 됩니다.

**Q. 신뢰도는 무엇입니까?**
A. AI가 해당 결과를 얼마나 확신하는지를 나타내는 값입니다.

**Q. 이미지가 조회되지 않습니다.**
A. 설비에서 이미지 업로드가 정상적으로 완료되었는지 확인하십시오.

**Q. 리뷰를 완료하면 수정할 수 있습니까?**
A. 완료 이후에는 관리자만 수정할 수 있습니다.

## 참고 자료 / 출처

- 원본 문서: `data/21 시스템 사용자 매뉴얼.md`

---

# 2. GLOSSARY-022 · AI Defect Inspection Platform 용어 사전

> doc_type: 용어 사전 · category: AI Defect Inspection Platform · version: v1.0 · created_date: 2026-07-02 · approval_status: pending · tags: [용어사전, 반도체, 웨이퍼, 검사프로세스, 모델, 메타데이터]

## 개요

AI Defect Inspection Platform은 반도체 장비에서 생성된 검사 이미지를 수집하고 AI 모델을 이용하여 양품(Good)/불량품(Bad)을 판정하는 플랫폼이다.
주요 기능은 데이터 수집, AI 추론, 결과 저장, 모델 관리, 모니터링이며, 주요 사용자는 운영자, AI 개발자, 공정 엔지니어이다.

| 항목 | 설명 |
| --- | --- |
| 플랫폼명 | AI Defect Inspection Platform |
| 목적 | 반도체 장비 검사 이미지 기반 양품/불량 판정 |
| 주요 기능 | 데이터 수집, AI 추론, 결과 저장, 모델 관리, 모니터링 |
| 주요 사용자 | 운영자, AI 개발자, 공정 엔지니어 |

## 예상 질문

- "Lot이 무엇인가요?"
- "Recipe와 Product의 차이가 무엇인가요?"
- "Model Version은 어디에서 확인하나요?"
- "Good/Bad는 어떤 기준으로 판정되나요?"
- "Confidence Score가 의미하는 것은 무엇인가요?"
- "Inference Time은 어느 단계에서 측정되나요?"
- "Transaction ID는 언제 생성되나요?"
- "데이터 생성일시와 적재일시의 차이는 무엇인가요?"

## 주요 내용

### 검사 프로세스

```
반도체 장비 → Image Capture → Data Collector → AI Inference Server → AI Model
→ Good / Bad 판정 → Result DB → Dashboard
```

### 주요 용어

| 용어 | 설명 |
| --- | --- |
| Inspection | 검사 공정 |
| AI Inference | AI 모델이 이미지를 분석하여 예측하는 과정 |
| Prediction | 모델이 생성한 판정 결과 |
| Good | 정상 제품 |
| Bad | 불량 제품 |
| Confidence Score | 모델이 판정한 신뢰도(0~100%) |
| Defect | 결함 |
| Defect Type | 결함 종류 |
| Inference Time | 모델 추론 시간 |
| Image | 장비에서 촬영한 검사 이미지 |

### 모델 용어

| 용어 | 설명 |
| --- | --- |
| Model | 딥러닝 학습 모델 |
| Model Name | 모델 이름 |
| Model Version | 모델 버전 |
| Model Type | Classification / Detection / Segmentation |
| Deploy Model | 운영 중인 모델 |
| Training Model | 학습 중인 모델 |
| Inference Model | 실제 판정에 사용되는 모델 |
| Accuracy | 정확도 |
| Precision | 정밀도 |
| Recall | 재현율 |
| F1 Score | 모델 성능 평가 지표 |
| Threshold | 양불 판정 기준값 |

### 데이터 용어

| 용어 | 설명 |
| --- | --- |
| Lot | 동일한 생산 조건으로 제조된 제품 묶음 |
| Wafer | 반도체 웨이퍼 |
| Wafer ID | 웨이퍼 식별 번호 |
| Carrier ID | 웨이퍼 Carrier 번호 |
| Recipe | 검사 조건 |
| Equipment ID | 검사 장비 ID |
| Product ID | 제품 번호 |
| Image ID | 이미지 식별 번호 |
| Inspection Time | 검사 수행 시간 |
| Created Time | 데이터 생성 일시 |
| Upload Time | 플랫폼 적재 시간 |
| File Name | 이미지 파일명 |
| File Path | 이미지 저장 위치 |
| Image Size | 이미지 크기 |
| Resolution | 이미지 해상도 |
| Channel | Gray / RGB |
| Format | PNG / JPG / TIFF |

### AI 결과 데이터

| 용어 | 설명 |
| --- | --- |
| Prediction Result | AI 판정 결과 |
| Prediction Score | 예측 확률 |
| Defect Label | 예측된 불량 종류 |
| Bounding Box | 결함 위치 |
| Mask | Segmentation 결과 |
| Heatmap | 모델이 판단한 중요 영역 |
| NG Reason | 불량 판정 사유 |

### 데이터 유입 정보

| 용어 | 설명 |
| --- | --- |
| Source System | 데이터를 전송한 시스템 |
| Request Body | 장비가 전달한 JSON 데이터 |
| API Version | API 버전 |
| Request Time | 요청 시간 |
| Receive Time | 플랫폼 수신 시간 |
| Transaction ID | 요청 식별 번호 |
| Batch ID | 배치 번호 |
| Retry Count | 재전송 횟수 |

### 운영 용어

| 용어 | 설명 |
| --- | --- |
| Data Collector | 장비 데이터를 수집하는 서비스 |
| Queue | 데이터 처리 대기열 |
| Worker | 데이터를 처리하는 프로세스 |
| Scheduler | 배치 수행 프로그램 |
| Dashboard | 운영 현황 화면 |
| Monitoring | 시스템 모니터링 |
| Log | 시스템 로그 |
| Alert | 장애 알림 |

### 데이터 흐름

```
장비(Image) → Image Collector → API Server → Validation → Storage
→ Inference Server → AI Model → Prediction → Result DB → Dashboard
```

### 주요 메타데이터

| 항목 | 설명 | 예시 |
| --- | --- | --- |
| Lot | 생산 Lot | LOT202606001 |
| Wafer ID | 웨이퍼 번호 | WF001 |
| Product | 제품명 | DRAM |
| Equipment | 장비번호 | EQ-001 |
| Recipe | 검사 Recipe | RCP-100 |
| Model | AI 모델 | Defect_v2 |
| Version | 모델 버전 | v2.1 |
| Prediction | 판정 | Good |
| Score | 신뢰도 | 98.5% |
| Created Time | 생성일시 | 2026-06-30 13:20:15 |
| Image Path | 이미지 위치 | /image/202606/... |

## 참고 자료 / 출처

- 원본 문서: `data/22 용어 사전.md`

---

# 3. MENU-001 · AI Defect Inspection Platform 메뉴 사용법

> doc_type: 메뉴 가이드 · category: AI Defect Inspection Platform · version: v1.0 · created_date: 2026-07-02 · approval_status: pending · tags: [메뉴가이드, Settings, Review, Model, Deployment, Monitoring] · related_menus: [Settings, Review, Model, Deployment, Monitoring]

## 개요

플랫폼은 반도체 장비에서 생성된 검사 이미지를 수집하고, AI 모델을 이용하여 양품/불량 판정을 수행한 후
모델을 지속적으로 개선하고 운영할 수 있도록 지원한다.

업무 흐름:

```
Settings(장비 연동·데이터 수집) → Review(데이터 검토·AI 판정 확인) → Model(AI 모델 학습)
→ Deployment(A/B Test·운영 배포) → Monitoring(운영 현황·모델 성능 모니터링)
```

## 예상 질문

- "신규 장비를 연결하려면 어떤 메뉴를 사용해야 하나요?"
- "AI 판정 결과는 어디에서 확인하나요?"
- "모델을 재학습하려면 어떤 절차를 따라야 하나요?"
- "A/B Test는 어느 메뉴에서 수행하나요?"
- "운영 중인 모델의 성능은 어디에서 모니터링하나요?"

## 주요 내용

### 1. Settings

**메뉴 목적**: 반도체 장비와 AI 플랫폼을 연동하여 검사 데이터를 정상적으로 수집할 수 있도록 설정하는 메뉴이다.

**주요 기능**
- 장비 등록 및 관리
- API Endpoint 설정
- 데이터 전송 규격(JSON) 설정
- Request Body 설정
- 이미지 저장 경로 설정
- 데이터 수집 활성화
- 장비별 Recipe 설정

**사용 시점**: 신규 장비를 연결하는 경우 / 데이터 전송 방식이 변경되는 경우 / API 또는 Request Body를 수정하는 경우

### 2. Review

**메뉴 목적**: 장비에서 수집된 검사 데이터와 AI 모델의 판정 결과를 확인하고 리뷰하는 메뉴이다.

**주요 기능**
- 수집된 이미지 조회
- AI 판정 결과 확인
- Confidence Score 확인
- 양품/불량 결과 확인
- 모델 버전 확인
- 불량 유형 확인
- 운영자의 리뷰 수행

**사용 시점**: AI 결과를 검토할 때 / 모델의 판정 결과를 확인할 때 / 오판 사례를 분석할 때

### 3. Model

**메뉴 목적**: AI 모델을 생성하고 학습하는 메뉴이다.

**주요 기능**
- 신규 모델 생성
- 학습 데이터 선택
- 학습 실행
- 모델 성능 확인
- Accuracy, Precision, Recall 확인
- 모델 버전 관리

**사용 시점**: 새로운 모델을 개발하는 경우 / 기존 모델을 재학습하는 경우 / 모델 성능을 개선하는 경우

### 4. Deployment

**메뉴 목적**: 학습이 완료된 AI 모델을 운영 환경에 배포하는 메뉴이다.

**주요 기능**
- 배포 대상 모델 선택
- 운영 모델 변경
- A/B Test 수행
- Canary 배포
- Rollback 수행
- 배포 이력 관리

**사용 시점**: 신규 모델을 운영에 적용하는 경우 / 기존 모델과 성능을 비교하는 경우 / 운영 모델을 변경하는 경우

### 5. Monitoring

**메뉴 목적**: 운영 중인 AI 모델과 데이터 처리 현황을 모니터링하는 메뉴이다.

**주요 기능**
- 모델 성능 추이
- 양품/불량 비율
- Confidence Score 추이
- 처리량(Throughput)
- 추론 시간(Inference Time)
- 모델별 운영 현황
- 이상 징후 모니터링

**사용 시점**: 모델 성능을 지속적으로 확인하는 경우 / 운영 현황을 모니터링하는 경우 / 모델 성능 저하 여부를 분석하는 경우

### 업무 시나리오 예시

**신규 장비 연동**
1. Settings에서 장비 및 데이터 전송 정보를 등록한다.
2. 장비에서 검사 이미지와 메타데이터를 플랫폼으로 전송한다.
3. Review에서 수집된 데이터와 AI 판정 결과를 확인한다.

**신규 모델 운영**
1. Model에서 새로운 AI 모델을 학습한다.
2. Deployment에서 기존 모델과 A/B Test를 수행한다.
3. 성능이 검증되면 운영 모델로 배포한다.
4. Monitoring에서 운영 중인 모델의 성능과 트렌드를 지속적으로 확인한다.

## 관련 메뉴 / 업무 절차

| 메뉴 | 목적 | 주요 사용자 | 다음 단계 |
| --- | --- | --- | --- |
| Settings | 장비와 플랫폼 연동 및 데이터 수집 환경 설정 | 운영자 | Review |
| Review | 수집된 데이터와 AI 판정 결과 검토 | 운영자, 공정 엔지니어 | Model |
| Model | AI 모델 학습 및 성능 평가 | AI 개발자 | Deployment |
| Deployment | 모델 A/B Test 및 운영 배포 | AI 개발자, 운영자 | Monitoring |
| Monitoring | 운영 모델 성능 및 서비스 현황 모니터링 | 운영자 | Model(재학습) 또는 Deployment(재배포) |

## 참고 자료 / 출처

- 원본 문서: `data/메뉴 사용법.md`
