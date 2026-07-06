import re
from dataclasses import dataclass
from typing import List

# 헤더(##, ###) 기준으로 섹션을 나눈 뒤, 긴 섹션은 500~1000 토큰(단어 수로 근사)
# 구간으로 15% 오버랩을 두고 슬라이딩 윈도우 분할한다.

_TARGET_WORDS = 650  # 500~1000 토큰 목표치의 중간값 근사
_OVERLAP_RATIO = 0.15

_H2_RE = re.compile(r"^##\s+(.*)")
_H3_RE = re.compile(r"^###\s+(.*)")


@dataclass
class MarkdownChunk:
    section: str
    text: str


@dataclass
class _HeadingSection:
    heading_path: str
    content: str


def _split_by_headings(body: str) -> List[_HeadingSection]:
    lines = body.split("\n")
    sections: List[_HeadingSection] = []
    current_path: List[str] = []
    current_heading_path = ""
    current_lines: List[str] = []

    def flush():
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(_HeadingSection(heading_path=current_heading_path, content=content))
        current_lines.clear()

    for line in lines:
        h3 = _H3_RE.match(line)
        h2 = _H2_RE.match(line) if not h3 else None

        if h2:
            flush()
            current_path[:] = [h2.group(1).strip()]
            current_heading_path = " > ".join(current_path)
        elif h3:
            flush()
            head = current_path[0] if current_path else ""
            current_path[:] = [p for p in [head, h3.group(1).strip()] if p]
            current_heading_path = " > ".join(current_path)
        current_lines.append(line)

    flush()
    return sections


def _window_words(words: List[str], target: int, overlap_ratio: float) -> List[List[str]]:
    if len(words) <= target:
        return [words]
    step = max(1, round(target * (1 - overlap_ratio)))
    windows: List[List[str]] = []
    start = 0
    while start < len(words):
        end = min(start + target, len(words))
        windows.append(words[start:end])
        if end >= len(words):
            break
        start += step
    return windows


def chunk_markdown(body: str) -> List[MarkdownChunk]:
    sections = _split_by_headings(body)
    chunks: List[MarkdownChunk] = []

    for section in sections:
        words = section.content.split()
        windows = _window_words(words, _TARGET_WORDS, _OVERLAP_RATIO)
        for idx, w in enumerate(windows):
            suffix = f" (part {idx + 1}/{len(windows)})" if len(windows) > 1 else ""
            chunks.append(
                MarkdownChunk(
                    section=(section.heading_path or "개요") + suffix,
                    text=" ".join(w),
                )
            )

    return chunks
