'use client';

import { create } from 'zustand';
import type { PullRequest } from '@/types/project';

/**
 * Open PullRequest 서버 캐시.
 *
 * plan §2.3 에 따라 서버 상태는 본래 SWR 영역이지만, 현재 단계에서는 단순
 * Zustand 캐시로 관리하고 `bumpRefresh` 를 통해 재로딩 트리거를 노출한다.
 */
interface PrState {
  openPRs: PullRequest[];
  loading: boolean;
  error: string | null;
  refreshNonce: number;

  setOpenPRs: (prs: PullRequest[]) => void;
  setLoading: (v: boolean) => void;
  setError: (msg: string | null) => void;
  bumpRefresh: () => void;
}

export const usePrStore = create<PrState>()((set) => ({
  openPRs: [],
  loading: false,
  error: null,
  refreshNonce: 0,
  setOpenPRs: (prs) => set({ openPRs: prs, loading: false, error: null }),
  setLoading: (v) => set({ loading: v }),
  setError: (msg) => set({ error: msg, loading: false }),
  bumpRefresh: () => set((s) => ({ refreshNonce: s.refreshNonce + 1 })),
}));
