'use client';

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { HitlData } from '@/types/agent-events';

export interface PendingHitl {
  threadId: string;
  sessionId: string;
  data: HitlData;
  createdAt: string;
  dismissedAt?: string;
}

interface HitlState {
  pendingByThreadId: Record<string, PendingHitl>;
  order: string[];
  activeThreadId: string | null;

  upsert: (hitl: PendingHitl) => void;
  dismissActive: () => void;
  openThread: (threadId: string) => void;
  openForSession: (sessionId: string) => void;
  remove: (threadId: string) => void;
  clearSession: (sessionId: string) => void;
}

function latestForSession(state: HitlState, sessionId: string) {
  for (let i = state.order.length - 1; i >= 0; i -= 1) {
    const threadId = state.order[i];
    const item = state.pendingByThreadId[threadId];
    if (item?.sessionId === sessionId) return item;
  }
  return null;
}

export const useHitlStore = create<HitlState>()(
  persist(
    (set) => ({
      pendingByThreadId: {},
      order: [],
      activeThreadId: null,

      upsert: (hitl) =>
        set((s) => {
          const exists = hitl.threadId in s.pendingByThreadId;
          return {
            pendingByThreadId: {
              ...s.pendingByThreadId,
              [hitl.threadId]: hitl,
            },
            order: exists ? s.order : [...s.order, hitl.threadId],
            activeThreadId: hitl.threadId,
          };
        }),

      dismissActive: () =>
        set((s) => {
          const threadId = s.activeThreadId;
          if (!threadId) return s;
          const item = s.pendingByThreadId[threadId];
          if (!item) return { activeThreadId: null };
          return {
            activeThreadId: null,
            pendingByThreadId: {
              ...s.pendingByThreadId,
              [threadId]: {
                ...item,
                dismissedAt: new Date().toISOString(),
              },
            },
          };
        }),

      openThread: (threadId) =>
        set((s) =>
          s.pendingByThreadId[threadId] ? { activeThreadId: threadId } : s,
        ),

      openForSession: (sessionId) =>
        set((s) => {
          const item = latestForSession(s, sessionId);
          return item ? { activeThreadId: item.threadId } : s;
        }),

      remove: (threadId) =>
        set((s) => {
          if (!(threadId in s.pendingByThreadId)) return s;
          const next = { ...s.pendingByThreadId };
          delete next[threadId];
          return {
            pendingByThreadId: next,
            order: s.order.filter((id) => id !== threadId),
            activeThreadId:
              s.activeThreadId === threadId ? null : s.activeThreadId,
          };
        }),

      clearSession: (sessionId) =>
        set((s) => {
          const removeIds = new Set(
            s.order.filter(
              (threadId) =>
                s.pendingByThreadId[threadId]?.sessionId === sessionId,
            ),
          );
          if (removeIds.size === 0) return s;
          const next = { ...s.pendingByThreadId };
          for (const threadId of removeIds) delete next[threadId];
          return {
            pendingByThreadId: next,
            order: s.order.filter((threadId) => !removeIds.has(threadId)),
            activeThreadId:
              s.activeThreadId && removeIds.has(s.activeThreadId)
                ? null
                : s.activeThreadId,
          };
        }),
    }),
    {
      name: 'aise-hitl-v1',
      storage: createJSONStorage(() => sessionStorage),
      partialize: (s) => ({
        pendingByThreadId: s.pendingByThreadId,
        order: s.order,
        activeThreadId: null,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) state.activeThreadId = null;
      },
    },
  ),
);

export function selectLatestPendingHitlForSession(
  state: HitlState,
  sessionId?: string,
) {
  if (!sessionId) return null;
  return latestForSession(state, sessionId);
}
