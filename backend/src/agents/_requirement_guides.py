"""RequirementAgent 전용 가이드 메시지 매핑.

`extract_records` 가 raise 하는 AppException.detail 문자열을 사용자가 다음
행동을 알 수 있는 친절한 안내 문구로 변환한다. LLM 호출 없이 정적 매핑만
사용 — 에러 케이스 수가 적고 가이드 문구는 결정적이어야 하므로.

각 가이드는 2-3줄, 다음 행동 + 대체 경로 (자유 입력 / 수동 폼) 을 함께
제시한다. 매칭되지 않는 detail 은 fallback 가이드를 사용한다.
"""
from __future__ import annotations


_GUIDE_BY_DETAIL: dict[str, str] = {
    "활성 지식 문서가 없습니다.": (
        "아직 분석할 지식 문서가 없습니다.\n"
        "좌측 사이드바의 '지식 문서' 메뉴에서 PDF·문서를 업로드하고 '활성' "
        "토글을 켜주세요. 그 다음 다시 '레코드 추출' 을 요청하시면 됩니다.\n"
        "또는 채팅창에 '우리 시스템은 ~~ 해야 한다' 같은 요구사항 문장을 "
        "직접 입력하셔도 좋고, 우측 'Records' 패널의 '직접 추가' 버튼으로 "
        "수동 등록도 가능합니다."
    ),
    "활성 섹션이 없습니다.": (
        "요구사항 섹션이 모두 비활성 상태입니다.\n"
        "우측 'Records' 패널의 '섹션 설정' 에서 FR / QA / 제약사항 등 "
        "사용할 섹션을 한 개 이상 활성화해 주세요.\n"
        "활성화 후 다시 추출을 요청하시면 진행됩니다."
    ),
}


_FALLBACK = (
    "요구사항 추출 중 일시적인 오류가 발생했습니다.\n"
    "잠시 후 다시 시도해 주시거나, 채팅창에 요구사항을 직접 입력해 주시면 "
    "바로 후보로 변환해 드립니다.\n"
    "오류가 계속되면 우측 'Records' 패널의 '직접 추가' 버튼으로 수동 등록도 "
    "가능합니다."
)


_NO_CANDIDATES = (
    "문서에서 요구사항 후보를 찾지 못했어요.\n"
    "지식 문서가 본문이 적거나 섹션 정의와 매치되지 않을 수 있습니다. "
    "더 풍부한 지식 문서를 추가하거나, 채팅에 '우리 시스템은 ~~ 해야 한다' "
    "같은 요구사항 문장을 직접 입력해 주세요.\n"
    "우측 'Records' 패널의 '직접 추가' 버튼으로 수동 등록도 가능합니다."
)


def to_user_friendly_guide(detail: str) -> str:
    """AppException.detail 을 사용자 친화 가이드로 변환.

    매핑되지 않는 메시지는 fallback 안내를 반환한다.
    """
    return _GUIDE_BY_DETAIL.get(detail.strip(), _FALLBACK)


def no_candidates_guide() -> str:
    """추출은 성공했지만 후보가 0개일 때의 안내."""
    return _NO_CANDIDATES


__all__ = ["no_candidates_guide", "to_user_friendly_guide"]
