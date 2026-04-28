import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ArtifactType = 'records' | 'srs' | 'design' | 'testcase';

export interface ArtifactVersion {
  version_id: string;
  version_number: number;
  artifact_type: ArtifactType;
  created_at: string;
  item_count: number;
}

/**
 * 탭 이동 시 "이 버전을 자동 선택하고 싶다" 같은 일회성 의도를 전달.
 * 예: Design 탭에서 "출처 보기" → SRS 탭으로 이동 + 입력으로 사용된 SRS
 *     ArtifactVersion.id 를 selectedSrsId 로 강제. 처리한 화면이 consume(null) 하여 1회성 보장.
 */
export interface ArtifactPendingFocus {
  kind: 'records' | 'srs' | 'design' | 'testcase';
  /** SRS/Design 의 경우 ArtifactVersion.id (= 화면의 selectedXxxId). */
  versionId?: string;
}

interface ArtifactState {
  activeTab: ArtifactType;
  setActiveTab: (tab: ArtifactType) => void;
  pendingFocus: ArtifactPendingFocus | null;
  setPendingFocus: (focus: ArtifactPendingFocus | null) => void;
}

export const useArtifactStore = create<ArtifactState>()(
  persist(
    (set) => ({
      activeTab: 'records',
      setActiveTab: (tab) => set({ activeTab: tab }),
      pendingFocus: null,
      setPendingFocus: (focus) => set({ pendingFocus: focus }),
    }),
    {
      name: 'aise-artifact',
      partialize: (s) => ({ activeTab: s.activeTab }),
    },
  ),
);
