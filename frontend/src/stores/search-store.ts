import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface RecentSearchItem {
  id: string;
  label: string;
  type: 'navigation' | 'project' | 'action';
  href?: string;
}

interface SearchState {
  recentItems: RecentSearchItem[];
  addRecentItem: (item: RecentSearchItem) => void;
  removeRecentItem: (id: string) => void;
  clearRecentItems: () => void;
}

const MAX_RECENT_ITEMS = 5;

export const useSearchStore = create<SearchState>()(
  persist(
    (set) => ({
      recentItems: [],

      addRecentItem: (item) =>
        set((s) => {
          const filtered = s.recentItems.filter((i) => i.id !== item.id);
          return { recentItems: [item, ...filtered].slice(0, MAX_RECENT_ITEMS) };
        }),

      removeRecentItem: (id) =>
        set((s) => ({ recentItems: s.recentItems.filter((i) => i.id !== id) })),

      clearRecentItems: () => set({ recentItems: [] }),
    }),
    {
      name: 'aise-search',
      partialize: (s) => ({ recentItems: s.recentItems }),
    },
  ),
);
