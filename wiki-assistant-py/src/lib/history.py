from typing import List


def recent_turns(history: List[dict], window_turns: int) -> List[dict]:
    """Window memory: 1턴 = 사용자+어시스턴트 한 쌍. 최근 window_turns턴만 남긴다.
    history는 항상 완결된 과거 턴만 담고 있다(현재 질문은 별도로 state["question"]에 있음)."""
    if not history:
        return []
    return history[-(window_turns * 2) :]


def format_history_block(history: List[dict]) -> str:
    if not history:
        return ""
    lines = []
    for turn in history:
        speaker = "사용자" if turn.get("role") == "user" else "어시스턴트"
        lines.append(f"{speaker}: {turn.get('text', '')}")
    return "\n".join(lines)
