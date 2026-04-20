import { create } from 'zustand';
import type { ReadinessResponse } from '@/types/project';
import { projectService } from '@/services/project-service';

interface ReadinessState {
  data: ReadinessResponse | null;
  loading: boolean;
  projectId: string | null;
  fetch: (projectId: string) => Promise<void>;
  invalidate: () => void;
}

export const useReadinessStore = create<ReadinessState>()((set, get) => ({
  data: null,
  loading: false,
  projectId: null,

  fetch: async (projectId: string) => {
    set({ loading: true, projectId });
    try {
      const data = await projectService.getReadiness(projectId);
      set({ data, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  invalidate: () => {
    const { projectId } = get();
    if (projectId) {
      get().fetch(projectId);
    }
  },
}));
