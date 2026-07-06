import sys

from .graph import build_graph


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('사용법: python -m src.ask "질문 내용"', file=sys.stderr)
        sys.exit(1)

    graph = build_graph()
    # 재시도 루프(최대 3회) 때문에 question_analyzer ~ query_rewriter 구간이 최대 4회 반복 실행될 수 있어
    # LangGraph 기본 recursion_limit(25)보다 넉넉하게 잡는다.
    try:
        result = graph.invoke(
            {"question": question, "original_question": question},
            config={"recursion_limit": 50},
        )
    except Exception as exc:  # noqa: BLE001 - 어떤 노드에서 실패하든(API 오류 등) 안내 메시지로 정상 종료시킨다.
        print("=" * 40)
        print(f"질문: {question}")
        print("-" * 40)
        print(
            f"[안내] 답변 생성 중 일시적인 오류가 발생하여 처리를 완료하지 못했습니다 "
            f"({exc.__class__.__name__}: {exc}).\n"
            "Gemini API 무료 티어 쿼터(분당/일일 호출 한도) 초과일 가능성이 높습니다. "
            "잠시 후 다시 시도해 주시거나, 계속되면 담당자에게 문의해 주세요."
        )
        print("=" * 40)
        sys.exit(1)

    print("=" * 40)
    print(f"질문: {question}")
    print(f"intent: {result.get('intent')} / keywords: {', '.join(result.get('keywords', []))}")
    print(
        f"confidence: {result.get('confidence_score', 0):.2f} / retry: {result.get('retry_count', 0)} "
        f"/ escalation: {result.get('escalation_required')}"
    )
    attempt_log = result.get("attempt_log", [])
    if attempt_log:
        print("-" * 40)
        print("[시도 로그]")
        for line in attempt_log:
            print(line)
    print("-" * 40)
    print(result.get("final_message", ""))
    print("=" * 40)


if __name__ == "__main__":
    main()
