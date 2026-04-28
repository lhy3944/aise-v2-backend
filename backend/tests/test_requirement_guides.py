"""사용자 친화 가이드 매핑 단위 테스트."""
from __future__ import annotations

from src.agents._requirement_guides import (
    no_candidates_guide,
    to_user_friendly_guide,
)


def test_known_detail_returns_specific_guide():
    guide = to_user_friendly_guide("활성 지식 문서가 없습니다.")
    assert "지식 문서" in guide
    assert "직접" in guide  # 대체 경로 안내 포함


def test_known_detail_with_whitespace_normalised():
    guide = to_user_friendly_guide("  활성 섹션이 없습니다.  ")
    assert "섹션" in guide
    assert "활성화" in guide


def test_unknown_detail_returns_fallback():
    guide = to_user_friendly_guide("LLM API rate limit exceeded")
    assert "일시적" in guide or "다시 시도" in guide


def test_no_candidates_guide_mentions_alternatives():
    guide = no_candidates_guide()
    assert "직접" in guide
    assert "후보" in guide
