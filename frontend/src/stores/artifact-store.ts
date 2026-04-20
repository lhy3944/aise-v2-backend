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

interface ArtifactState {
  activeTab: ArtifactType;
  setActiveTab: (tab: ArtifactType) => void;
}

export const useArtifactStore = create<ArtifactState>()(
  persist(
    (set) => ({
      activeTab: 'records',
      setActiveTab: (tab) => set({ activeTab: tab }),
    }),
    {
      name: 'aise-artifact',
      partialize: (s) => ({ activeTab: s.activeTab }),
    },
  ),
);
