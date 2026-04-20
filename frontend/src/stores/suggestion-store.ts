import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface PromptCard {
  title: string;
  description: string;
}

interface CachedSuggestion {
  fingerprint: string;
  cards: PromptCard[];
}

interface SuggestionState {
  /** 프로젝트별 캐시: projectId → { fingerprint, cards } */
  cache: Record<string, CachedSuggestion>;

  /** 캐시된 카드 조회 */
  getCached: (projectId: string) => CachedSuggestion | null;
  /** 캐시 저장 */
  setCache: (projectId: string, fingerprint: string, cards: PromptCard[]) => void;
}

export const useSuggestionStore = create<SuggestionState>()(
  persist(
    (set, get) => ({
      cache: {},

      getCached: (projectId) => get().cache[projectId] ?? null,

      setCache: (projectId, fingerprint, cards) =>
        set((s) => ({
          cache: { ...s.cache, [projectId]: { fingerprint, cards } },
        })),
    }),
    {
      name: 'aise-suggestions',
      partialize: (s) => ({ cache: s.cache }),
    },
  ),
);
