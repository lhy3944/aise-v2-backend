import { create } from 'zustand';
import type { ArtifactKind } from '@/types/agent-events';

/**
 * 모든 artifact 타입(record/srs/design/testcase) 의 list 갱신 트리거를 한 곳에서 관리.
 *
 * staging-store 와 ChangesWorkspaceModal 은 도메인을 모르므로 PR 머지 시
 * `bumpAll()` 을 부르고, 각 artifact 화면(ArtifactRecordsPanel/SrsArtifact/...)
 * 은 자기 kind 의 nonce 만 구독해 useEffect 의 의존성으로 사용한다.
 *
 * 도메인-전용 흐름(예: record 추출 후 bump) 은 `bump(kind)` 로 단일 타입만
 * 갱신할 수 있다.
 */
interface ArtifactRefreshState {
  nonce: Record<ArtifactKind, number>;
  bump: (kind: ArtifactKind) => void;
  bumpAll: () => void;
}

export const useArtifactRefreshStore = create<ArtifactRefreshState>()((set) => ({
  nonce: { record: 0, srs: 0, design: 0, testcase: 0 },
  bump: (kind) =>
    set((s) => ({ nonce: { ...s.nonce, [kind]: s.nonce[kind] + 1 } })),
  bumpAll: () =>
    set((s) => ({
      nonce: {
        record: s.nonce.record + 1,
        srs: s.nonce.srs + 1,
        design: s.nonce.design + 1,
        testcase: s.nonce.testcase + 1,
      },
    })),
}));
