"""text_chunker 마크다운 블록 보존 테스트"""

import pytest

from src.utils.text_chunker import chunk_text


class TestMarkdownTablePreservation:
    """테이블이 하나의 청크에 보존되는지 확인"""

    def test_small_table_stays_in_one_chunk(self):
        md = (
            "# 제목\n\n"
            "설명 텍스트입니다.\n\n"
            "| 컬럼1 | 컬럼2 | 컬럼3 |\n"
            "|-------|-------|-------|\n"
            "| A     | B     | C     |\n"
            "| D     | E     | F     |\n\n"
            "끝 문단입니다."
        )
        chunks = chunk_text(md, max_tokens=500, overlap_tokens=50, file_type="md")

        # 테이블이 포함된 청크를 찾음
        table_chunks = [c for c in chunks if "|-------|" in c]
        assert len(table_chunks) >= 1

        # 테이블 헤더와 모든 행이 같은 청크에 있어야 함
        table_chunk = table_chunks[0]
        assert "| 컬럼1 | 컬럼2 | 컬럼3 |" in table_chunk
        assert "|-------|-------|-------|" in table_chunk
        assert "| A     | B     | C     |" in table_chunk
        assert "| D     | E     | F     |" in table_chunk

    def test_large_table_splits_with_header_preserved(self):
        """대형 테이블 분할 시 각 청크에 헤더행이 복제되어야 함"""
        header = "| ID | Name | Description |\n|-----|------|-------------|\n"
        rows = "".join(f"| {i} | item{i} | description for item {i} that is long enough |\n" for i in range(100))
        md = f"# 큰 테이블\n\n{header}{rows}"

        chunks = chunk_text(md, max_tokens=100, overlap_tokens=10, file_type="md")

        # 테이블을 포함하는 모든 청크에 헤더가 있어야 함
        table_chunks = [c for c in chunks if "|-----|" in c]
        assert len(table_chunks) >= 2, "대형 테이블은 여러 청크로 분할되어야 함"

        for chunk in table_chunks:
            assert "| ID | Name | Description |" in chunk, "각 청크에 테이블 헤더가 있어야 함"
            assert "|-----|------|-------------|" in chunk, "각 청크에 구분자 행이 있어야 함"


class TestMarkdownCodeBlockPreservation:
    """코드블록이 분할되지 않는지 확인"""

    def test_code_block_stays_in_one_chunk(self):
        md = (
            "# 코드 예제\n\n"
            "아래는 파이썬 코드입니다:\n\n"
            "```python\n"
            "def hello():\n"
            '    print("Hello, world!")\n'
            "    return True\n"
            "```\n\n"
            "위 코드를 실행하세요."
        )
        chunks = chunk_text(md, max_tokens=500, overlap_tokens=50, file_type="md")

        # 코드블록이 포함된 청크를 찾음
        code_chunks = [c for c in chunks if "```python" in c]
        assert len(code_chunks) >= 1

        code_chunk = code_chunks[0]
        # 여는 ``` 와 닫는 ``` 가 같은 청크에 있어야 함
        assert code_chunk.count("```") >= 2, "코드블록의 여닫기가 같은 청크에 있어야 함"
        assert 'print("Hello, world!")' in code_chunk


class TestMarkdownListPreservation:
    """리스트가 항목 단위로 분할되는지 확인"""

    def test_short_list_stays_in_one_chunk(self):
        md = (
            "# 할 일 목록\n\n"
            "- 첫 번째 항목\n"
            "- 두 번째 항목\n"
            "- 세 번째 항목\n\n"
            "끝 문단."
        )
        chunks = chunk_text(md, max_tokens=500, overlap_tokens=50, file_type="md")

        list_chunks = [c for c in chunks if "- 첫 번째 항목" in c]
        assert len(list_chunks) >= 1

        list_chunk = list_chunks[0]
        assert "- 두 번째 항목" in list_chunk
        assert "- 세 번째 항목" in list_chunk


class TestMarkdownBlockBoundaries:
    """청크 간 경계에서 \n\n이 보존되는지 확인"""

    def test_chunks_joined_with_double_newline(self):
        """청크를 결합할 때 \n\n으로 합치면 원본 구조가 복원되어야 함"""
        md = (
            "# 제목 1\n\n"
            "문단 A 입니다.\n\n"
            "## 제목 2\n\n"
            "문단 B 입니다.\n\n"
            "### 제목 3\n\n"
            "문단 C 입니다."
        )
        chunks = chunk_text(md, max_tokens=50, overlap_tokens=0, file_type="md")

        # 각 청크의 끝이나 시작에 불완전한 단일 \n만 있으면 안 됨
        for chunk in chunks:
            # 헤더(#)로 시작하는 라인이 있다면, 그 앞에 내용이 있을 때 \n\n으로 분리되어야 함
            lines = chunk.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("#") and i > 0 and lines[i - 1].strip():
                    # 헤더 앞에 비어있지 않은 라인이 있으면 \n\n 분리가 필요
                    preceding = "\n".join(lines[:i])
                    assert preceding.endswith("\n"), "헤더 앞에 빈 줄이 있어야 함"


class TestTxtFileUnchanged:
    """txt 파일 처리가 기존과 동일한지 확인"""

    def test_txt_uses_sentence_splitting(self):
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        chunks_txt = chunk_text(text, max_tokens=10, overlap_tokens=0, file_type="txt")
        chunks_md = chunk_text(text, max_tokens=10, overlap_tokens=0, file_type="md")

        # txt는 문장 분할을 사용하므로 md와 다른 결과를 낼 수 있음
        # (둘 다 작동하지만 분할 전략이 다름)
        assert len(chunks_txt) >= 1
        assert len(chunks_md) >= 1

    def test_empty_text_returns_empty(self):
        assert chunk_text("", file_type="txt") == []
        assert chunk_text("", file_type="md") == []
        assert chunk_text("   ", file_type="md") == []


class TestPreviewSafeTruncation:
    """미리보기 안전 자르기 테스트"""

    def test_safe_truncate_at_block_boundary(self):
        from src.services.knowledge_svc import _safe_truncate_md

        text = "# 제목\n\n문단 1 입니다.\n\n## 소제목\n\n문단 2 입니다."
        # 중간에서 자를 때 \n\n 경계에서 잘라야 함
        result = _safe_truncate_md(text, 20)
        assert result.endswith("\n\n") or "\n\n" not in result[len(result) - 5 :]

    def test_truncate_closes_open_code_block(self):
        from src.services.knowledge_svc import _safe_truncate_md

        text = "설명\n\n```python\ndef hello():\n    pass\n```\n\n끝"
        # 코드블록 중간에서 잘리면 닫는 ``` 가 추가되어야 함
        result = _safe_truncate_md(text, 30)
        backtick_count = result.count("```")
        assert backtick_count % 2 == 0, "열린 코드블록은 닫혀야 함"

    def test_no_truncation_when_within_limit(self):
        from src.services.knowledge_svc import _safe_truncate_md

        text = "짧은 텍스트"
        assert _safe_truncate_md(text, 1000) == text
