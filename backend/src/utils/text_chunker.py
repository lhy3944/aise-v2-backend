"""텍스트 청킹 유틸리티 -- tiktoken 기반 재귀 문자 분할

마크다운 파일은 구조 인식 청킹을 사용하여 테이블, 코드블록, 리스트 등의
마크다운 블록이 청크 경계에서 잘리지 않도록 보존한다.
"""

import re
from dataclasses import dataclass

import tiktoken

_encoding = None

# 리스트 항목: -, *, +, 숫자. 로 시작 (들여쓰기 허용)
_LIST_ITEM_RE = re.compile(r"^\s*[-*+]\s|^\s*\d+\.\s")
# 테이블 행: |로 시작
_TABLE_ROW_RE = re.compile(r"^\s*\|")
# 헤더: #로 시작
_HEADER_RE = re.compile(r"^#{1,6}\s")


def _get_encoding():
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def _token_count(text: str) -> int:
    return len(_get_encoding().encode(text))


def _split_by_separators(text: str, separators: list[str]) -> tuple[list[str], str]:
    """첫 번째로 매칭되는 구분자로 분할한다. 모두 실패하면 단어 단위로 분할."""
    for sep in separators:
        parts = text.split(sep)
        if len(parts) > 1:
            result = [part for part in parts if part]
            return result, sep
    return text.split(), " "


# ---------------------------------------------------------------------------
# 마크다운 블록 파싱 — 줄 단위(line-based)
# ---------------------------------------------------------------------------

@dataclass
class _MdBlock:
    content: str
    block_type: str  # "code", "table", "list", "text", "header"


def _parse_md_blocks(text: str) -> list[_MdBlock]:
    """마크다운 텍스트를 줄 단위로 순회하며 원자적 블록으로 분류한다.

    줄 유형별 그룹핑:
    - ``` 사이의 줄 → code 블록
    - | 로 시작하는 연속 줄 → table 블록
    - -/*/+/숫자. 로 시작하는 연속 줄 → list 블록
    - # 로 시작하는 줄 → header 블록 (단독)
    - 그 외 → text 블록 (연속된 일반 줄)
    """
    lines = text.split("\n")
    blocks: list[_MdBlock] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 빈 줄 스킵
        if not stripped:
            i += 1
            continue

        # 코드블록: ``` 로 시작하면 닫는 ``` 까지 수집
        if stripped.startswith("```"):
            code_lines = [line]
            i += 1
            while i < len(lines):
                code_lines.append(lines[i])
                if lines[i].strip().startswith("```") and len(code_lines) > 1:
                    i += 1
                    break
                i += 1
            blocks.append(_MdBlock(content="\n".join(code_lines), block_type="code"))
            continue

        # 테이블: | 로 시작하는 연속 줄 수집
        if _TABLE_ROW_RE.match(line):
            table_lines = []
            while i < len(lines) and _TABLE_ROW_RE.match(lines[i]):
                table_lines.append(lines[i])
                i += 1
            blocks.append(_MdBlock(content="\n".join(table_lines), block_type="table"))
            continue

        # 헤더: # 로 시작 → 단독 블록
        if _HEADER_RE.match(stripped):
            blocks.append(_MdBlock(content=line, block_type="header"))
            i += 1
            continue

        # 리스트: -/*/+/숫자. 로 시작하는 연속 줄 수집
        if _LIST_ITEM_RE.match(line):
            list_lines = []
            while i < len(lines):
                ln = lines[i]
                # 리스트 항목이거나 들여쓰기된 연속줄이면 같은 리스트
                if _LIST_ITEM_RE.match(ln) or (ln.startswith("   ") and list_lines):
                    list_lines.append(ln)
                    i += 1
                else:
                    break
            blocks.append(_MdBlock(content="\n".join(list_lines), block_type="list"))
            continue

        # 일반 텍스트: 구조적 마커가 없는 연속 줄 수집
        text_lines = []
        while i < len(lines):
            ln = lines[i]
            s = ln.strip()
            if not s:
                # 빈 줄은 텍스트 블록 종료
                i += 1
                break
            if (
                s.startswith("```")
                or _TABLE_ROW_RE.match(ln)
                or _HEADER_RE.match(s)
                or _LIST_ITEM_RE.match(ln)
            ):
                break
            text_lines.append(ln)
            i += 1
        if text_lines:
            blocks.append(_MdBlock(content="\n".join(text_lines), block_type="text"))

    return blocks


# ---------------------------------------------------------------------------
# 대형 블록 분할
# ---------------------------------------------------------------------------

def _split_large_table(table: str, max_tokens: int) -> list[str]:
    """대형 테이블을 헤더를 보존하며 행 단위로 분할한다."""
    lines = table.split("\n")
    if len(lines) < 3:
        return [table]

    header_lines = lines[:2]
    header = "\n".join(header_lines)
    header_tokens = _token_count(header)
    data_lines = lines[2:]

    chunks: list[str] = []
    current_rows: list[str] = []
    current_tokens = header_tokens

    for row in data_lines:
        row_tokens = _token_count(row)
        if current_tokens + row_tokens > max_tokens and current_rows:
            chunks.append(header + "\n" + "\n".join(current_rows))
            current_rows = []
            current_tokens = header_tokens
        current_rows.append(row)
        current_tokens += row_tokens

    if current_rows:
        chunks.append(header + "\n" + "\n".join(current_rows))

    return chunks


def _split_large_code_block(code: str, max_tokens: int) -> list[str]:
    """대형 코드블록을 ```를 보존하며 줄 단위로 분할한다."""
    lines = code.split("\n")
    if len(lines) < 3:
        return [code]

    opener = lines[0]
    # 닫는 fence가 존재하지 않는(= truncated/malformed) 블록 보호:
    # lines[-1]이 fence가 아니면 실제 content이므로 body에 포함시키고 closer를 합성한다.
    if lines[-1].strip().startswith("```"):
        closer = lines[-1]
        body_lines = lines[1:-1]
    else:
        closer = "```"
        body_lines = lines[1:]

    overhead = _token_count(opener) + _token_count(closer)
    body_budget = max_tokens - overhead

    if body_budget <= 0:
        return [code]

    chunks: list[str] = []
    current_lines: list[str] = []
    current_tokens = 0

    for line in body_lines:
        line_tokens = _token_count(line)
        if current_tokens + line_tokens > body_budget and current_lines:
            chunks.append(opener + "\n" + "\n".join(current_lines) + "\n" + closer)
            current_lines = []
            current_tokens = 0
        current_lines.append(line)
        current_tokens += line_tokens

    if current_lines:
        chunks.append(opener + "\n" + "\n".join(current_lines) + "\n" + closer)

    return chunks


def _split_large_list(list_text: str, max_tokens: int) -> list[str]:
    """대형 리스트를 항목 단위로 분할한다."""
    lines = list_text.split("\n")
    chunks: list[str] = []
    current_items: list[str] = []
    current_tokens = 0

    for line in lines:
        if not line.strip():
            continue
        line_tokens = _token_count(line)
        if current_tokens + line_tokens > max_tokens and current_items:
            chunks.append("\n".join(current_items))
            current_items = []
            current_tokens = 0
        current_items.append(line)
        current_tokens += line_tokens

    if current_items:
        chunks.append("\n".join(current_items))

    return chunks


def _split_large_text(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """대형 텍스트를 줄 단위로 분할한다. 줄이 1개면 단어 단위 fallback."""
    lines = text.split("\n")

    # 여러 줄이면 줄 단위 분할 (줄바꿈 보존)
    if len(lines) > 1:
        chunks: list[str] = []
        current_lines: list[str] = []
        current_tokens = 0
        for line in lines:
            lt = _token_count(line)
            if current_tokens + lt > max_tokens and current_lines:
                chunks.append("\n".join(current_lines))
                current_lines = []
                current_tokens = 0
            current_lines.append(line)
            current_tokens += lt
        if current_lines:
            chunks.append("\n".join(current_lines))
        return chunks

    # 단일 줄: 단어 단위 분할
    words = text.split()
    chunks = []
    word_parts: list[str] = []
    word_tokens = 0

    for word in words:
        wt = _token_count(word)
        if word_tokens + wt > max_tokens and word_parts:
            chunks.append(" ".join(word_parts))
            overlap_parts: list[str] = []
            overlap_t = 0
            for w in reversed(word_parts):
                wt2 = _token_count(w)
                if overlap_t + wt2 > overlap_tokens:
                    break
                overlap_parts.insert(0, w)
                overlap_t += wt2
            word_parts = overlap_parts
            word_tokens = overlap_t
        word_parts.append(word)
        word_tokens += wt

    if word_parts:
        chunks.append(" ".join(word_parts))

    return chunks


# ---------------------------------------------------------------------------
# 마크다운 청킹 메인
# ---------------------------------------------------------------------------

def _chunk_markdown(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """마크다운 구조를 인식하여 청킹한다.

    2단계 파이프라인:
    1. 줄 단위 블록 파싱: 코드블록, 테이블, 리스트, 헤더, 일반 텍스트로 분류
    2. 토큰 기반 그룹핑: max_tokens 내에서 블록들을 합침 (\\n\\n 구분)
    """
    blocks = _parse_md_blocks(text)

    if not blocks:
        return []

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for block in blocks:
        block_tokens = _token_count(block.content)

        # 대형 블록: 유형별 분할 전략
        if block_tokens > max_tokens:
            if current_parts:
                chunks.append("\n\n".join(current_parts))
                current_parts = []
                current_tokens = 0

            if block.block_type == "table":
                chunks.extend(_split_large_table(block.content, max_tokens))
            elif block.block_type == "code":
                chunks.extend(_split_large_code_block(block.content, max_tokens))
            elif block.block_type == "list":
                chunks.extend(_split_large_list(block.content, max_tokens))
            else:
                chunks.extend(_split_large_text(block.content, max_tokens, overlap_tokens))
            continue

        # 현재 청크에 추가하면 초과하는 경우
        if current_tokens + block_tokens > max_tokens and current_parts:
            chunks.append("\n\n".join(current_parts))
            overlap_parts: list[str] = []
            overlap_t = 0
            for part in reversed(current_parts):
                pt = _token_count(part)
                if overlap_t + pt > overlap_tokens:
                    break
                overlap_parts.insert(0, part)
                overlap_t += pt
            current_parts = overlap_parts
            current_tokens = overlap_t

        current_parts.append(block.content)
        current_tokens += block_tokens

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50,
    file_type: str = "txt",
) -> list[str]:
    """텍스트를 max_tokens 이하의 청크로 분할한다.

    마크다운(md) 파일은 구조 인식 청킹을 사용하여 테이블, 코드블록,
    리스트가 청크 경계에서 잘리지 않도록 보존한다.

    일반 텍스트(txt 등)는 재귀 문자 분할 전략:
    1. 문단 (\\n\\n) 으로 분할
    2. 줄바꿈 (\\n) 으로 분할
    3. 문장 (. ! ?) 으로 분할
    4. 단어 단위로 분할
    """
    if not text or not text.strip():
        return []

    text = text.strip()

    if _token_count(text) <= max_tokens:
        return [text]

    # 마크다운: 구조 인식 청킹
    if file_type == "md":
        return _chunk_markdown(text, max_tokens, overlap_tokens)

    # 일반 텍스트: 기존 재귀 문자 분할
    separators = ["\n\n", "\n", ". ", "! ", "? "]
    segments, join_sep = _split_by_separators(text, separators)

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for segment in segments:
        seg_tokens = _token_count(segment)

        if seg_tokens > max_tokens:
            if current_parts:
                chunks.append(join_sep.join(current_parts))
                current_parts = []
                current_tokens = 0
            words = segment.split()
            word_parts: list[str] = []
            word_tokens = 0
            for word in words:
                wt = _token_count(word)
                if word_tokens + wt > max_tokens and word_parts:
                    chunks.append(" ".join(word_parts))
                    overlap_parts: list[str] = []
                    overlap_t = 0
                    for w in reversed(word_parts):
                        wt2 = _token_count(w)
                        if overlap_t + wt2 > overlap_tokens:
                            break
                        overlap_parts.insert(0, w)
                        overlap_t += wt2
                    word_parts = overlap_parts
                    word_tokens = overlap_t
                word_parts.append(word)
                word_tokens += wt
            if word_parts:
                current_parts = [" ".join(word_parts)]
                current_tokens = word_tokens
            continue

        if current_tokens + seg_tokens > max_tokens and current_parts:
            chunks.append(join_sep.join(current_parts))
            overlap_parts = []
            overlap_t = 0
            for part in reversed(current_parts):
                pt = _token_count(part)
                if overlap_t + pt > overlap_tokens:
                    break
                overlap_parts.insert(0, part)
                overlap_t += pt
            current_parts = overlap_parts
            current_tokens = overlap_t

        current_parts.append(segment)
        current_tokens += seg_tokens

    if current_parts:
        chunks.append(join_sep.join(current_parts))

    return chunks
