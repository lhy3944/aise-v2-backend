"""순서 변경(reorder) 관련 유틸리티."""

from collections.abc import Iterable
from typing import Hashable, TypeVar

T = TypeVar("T", bound=Hashable)


def dedupe_preserve_order(values: Iterable[T]) -> list[T]:
    """입력 순서를 유지한 채 중복 요소를 제거한다."""
    seen: set[T] = set()
    deduped: list[T] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def build_reordered_ids(requested_ids: Iterable[T], current_ids: Iterable[T]) -> list[T]:
    """부분 순서 변경 요청을 전체 순서로 확장한다.

    - `requested_ids`: 사용자가 순서를 지정한 ID 목록(부분 목록 가능)
    - `current_ids`: 현재 저장된 전체 ID 순서

    반환값은 `requested_ids`를 앞에 반영하고, 나머지 ID는 기존 상대 순서를 유지한 전체 순서다.
    """
    current = list(current_ids)
    if not current:
        return []

    current_set = set(current)
    requested = [rid for rid in dedupe_preserve_order(requested_ids) if rid in current_set]
    if not requested:
        return current

    requested_set = set(requested)
    remaining = [rid for rid in current if rid not in requested_set]
    return [*requested, *remaining]
