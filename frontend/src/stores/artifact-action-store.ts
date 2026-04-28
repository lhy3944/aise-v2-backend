import { create } from 'zustand';
import type { ArtifactKind } from '@/types/agent-events';

/**
 * artifact 타입별 진행 중 액션 상태 — 탭 unmount 후 재mount 되어도 유지된다.
 *
 * - generating: SRS/Design/TC 자동 생성 호출 중
 *
 * 컴포넌트는 액션 시작/완료 시 setGenerating 만 호출하면 되고, 다른 탭 라벨이나
 * 화면도 같은 nonce 를 구독해 spinner 를 보여줄 수 있다.
 */
interface ArtifactActionState {
  generating: Record<ArtifactKind, boolean>;
  setGenerating: (kind: ArtifactKind, value: boolean) => void;
}

export const useArtifactActionStore = create<ArtifactActionState>()((set) => ({
  generating: { record: false, srs: false, design: false, testcase: false },
  setGenerating: (kind, value) =>
    set((s) => ({ generating: { ...s.generating, [kind]: value } })),
}));
