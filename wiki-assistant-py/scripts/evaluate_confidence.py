# CONFIDENCE_THRESHOLD를 감이 아니라 실측 데이터로 정하기 위한 평가 스크립트.
# 긍정(위키에 실제로 답이 있는 질문)/부정(위키와 무관해서 답할 수 없어야 정상인 질문) 세트를 각각
# question_analyzer -> query_optimizer -> wiki_retriever -> document_reranker -> context_builder
# -> confidence_checker 파이프라인(재시도 루프 없이 단발)에 통과시켜 confidence_score 분포를 뽑는다.
# 사용법: python -m scripts.evaluate_confidence
import logging
import statistics

logging.disable(logging.CRITICAL)  # 노드별 상세 로그는 끄고 결과 표만 출력한다.

from src.nodes.confidence_checker import confidence_checker
from src.nodes.context_builder import context_builder
from src.nodes.document_reranker import document_reranker
from src.nodes.query_optimizer import query_optimizer
from src.nodes.question_analyzer import question_analyzer
from src.nodes.wiki_retriever import wiki_retriever

# 긍정 세트: wiki/02-glossary.md, wiki/03-menu-guide.md, wiki/01-ai-vision-inspection-manual.md에
# 실제로 답이 있는 질문들.
POSITIVE_QUESTIONS = [
    "Lot이 무엇인가요?",
    "Recipe와 Product의 차이가 무엇인가요?",
    "Confidence Score가 의미하는 것은 무엇인가요?",
    "GOOD과 DEFECT의 차이는?",
    "Review 메뉴는 어떤 역할을 해?",
    "Deployment 메뉴에서 뭘 할 수 있어?",
    "A/B Test는 어느 메뉴에서 수행하나요?",
    "Model 메뉴의 주요 기능은?",
    "Monitoring에서 뭘 확인할 수 있어?",
    "Wafer ID가 뭐야?",
    "Threshold의 의미는?",
    "신규 장비를 연결하려면 어떤 메뉴를 써야 해?",
    "Inference Time은 무엇을 의미하나요?",
    "Canary 배포가 뭐야?",
    "Transaction ID는 언제 생성돼?",
]

# 부정 세트: 플랫폼 위키와 무관하거나(잡담/일반상식), 위키에 없는 기능을 마치 있는 것처럼 묻는 질문.
NEGATIVE_QUESTIONS = [
    "오늘 서울 날씨 어때?",
    "가장 맛있는 라면 브랜드는?",
    "이 플랫폼에서 주식 투자 추천해줘",
    "삼국지 등장인물 알려줘",
    "이 플랫폼에 블록체인 지갑 연동 기능이 있어?",
    "GPT-4는 몇 개의 파라미터를 가지고 있어?",
    "오늘 점심 뭐 먹을까?",
    "이 플랫폼의 CEO는 누구야?",
    "양자컴퓨터 원리를 설명해줘",
    "이 플랫폼에서 암호화폐 채굴이 가능해?",
]


def _run_single_pass(question: str) -> dict:
    """재시도 루프 없이 단발로 confidence_score까지만 계산한다(own 컬렉션 기준)."""
    state = {"question": question, "original_question": question}
    state.update(question_analyzer(state))
    state.update(query_optimizer(state))
    state.update(wiki_retriever(state))
    state.update(document_reranker(state))
    state.update(context_builder(state))
    state.update(confidence_checker(state))
    return state


def _summarize(label: str, scores: list) -> None:
    print(f"{label}: n={len(scores)}  min={min(scores):.3f}  max={max(scores):.3f}  "
          f"mean={statistics.mean(scores):.3f}  median={statistics.median(scores):.3f}")


def main() -> None:
    print("=" * 70)
    print("긍정 세트 (위키에 실제로 답이 있는 질문)")
    print("=" * 70)
    positive_scores = []
    for q in POSITIVE_QUESTIONS:
        state = _run_single_pass(q)
        score = state["confidence_score"]
        positive_scores.append(score)
        print(f"[{score:.3f}] {q}")

    print()
    print("=" * 70)
    print("부정 세트 (답할 수 없어야 정상인 질문)")
    print("=" * 70)
    negative_scores = []
    for q in NEGATIVE_QUESTIONS:
        state = _run_single_pass(q)
        score = state["confidence_score"]
        negative_scores.append(score)
        print(f"[{score:.3f}] {q}")

    print()
    print("=" * 70)
    print("요약")
    print("=" * 70)
    _summarize("긍정 세트", positive_scores)
    _summarize("부정 세트", negative_scores)

    overlap = [s for s in positive_scores if s <= max(negative_scores)]
    print()
    if overlap:
        print(
            f"긍정 세트 중 부정 세트 최댓값({max(negative_scores):.3f}) 이하인 질문 {len(overlap)}건 "
            "-> 두 그룹이 겹치는 구간이 있어 threshold 하나로 완벽히 못 가를 수 있음"
        )
    else:
        print(
            f"긍정 세트 최솟값({min(positive_scores):.3f}) > 부정 세트 최댓값({max(negative_scores):.3f}) "
            "-> 그 사이 어디든 threshold로 두 그룹을 완전히 분리 가능"
        )
        print(f"추천 threshold(중간값): {(min(positive_scores) + max(negative_scores)) / 2:.3f}")


if __name__ == "__main__":
    main()
