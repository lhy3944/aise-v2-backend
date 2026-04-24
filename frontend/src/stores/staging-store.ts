'use client';

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

/**
 * 로컬 편집 드래프트 — Unstaged / Staged 2단계.
 *
 * plan §2.3 에 따라 staging-store 는 서버 상태가 아닌 UI 버퍼 전용.
 * 서버 호출 전까지 새로고침 방어 목적으로 sessionStorage 에 persist.
 *
 * 상태 전이:
 *   [edit] ─► unstaged ─stage──► staged ─createPR──► (server) ─► cleared
 *                 ▲                │
 *                 └─── unstage ────┘
 */
export interface ArtifactDraft {
  artifactId: string;
  content: string;
  originalContent: string;
  editedAt: string;
}

interface StagingState {
  unstagedArtifacts: { [artifactId: string]: ArtifactDraft };
  stagedArtifacts: { [artifactId: string]: ArtifactDraft };

  // Unstaged CRUD
  setArtifactDraft: (draft: ArtifactDraft) => void;
  discardArtifactDraft: (artifactId: string) => void;

  // Stage 전이
  stageArtifact: (artifactId: string) => void;
  stageAll: () => void;
  unstageArtifact: (artifactId: string) => void;

  // Staged CRUD
  discardStagedArtifact: (artifactId: string) => void;

  // 서버 반영 완료 — 해당 artifact 의 드래프트 모두 제거
  clearArtifact: (artifactId: string) => void;

  clearAll: () => void;
}

export const useStagingStore = create<StagingState>()(
  persist(
    (set) => ({
      unstagedArtifacts: {},
      stagedArtifacts: {},

      setArtifactDraft: (draft) =>
        set((s) => ({
          unstagedArtifacts: { ...s.unstagedArtifacts, [draft.artifactId]: draft },
        })),

      discardArtifactDraft: (artifactId) =>
        set((s) => {
          if (!(artifactId in s.unstagedArtifacts)) return s;
          const next = { ...s.unstagedArtifacts };
          delete next[artifactId];
          return { unstagedArtifacts: next };
        }),

      stageArtifact: (artifactId) =>
        set((s) => {
          const draft = s.unstagedArtifacts[artifactId];
          if (!draft) return s;
          const nextUnstaged = { ...s.unstagedArtifacts };
          delete nextUnstaged[artifactId];
          return {
            unstagedArtifacts: nextUnstaged,
            stagedArtifacts: { ...s.stagedArtifacts, [artifactId]: draft },
          };
        }),

      stageAll: () =>
        set((s) => ({
          unstagedArtifacts: {},
          stagedArtifacts: { ...s.stagedArtifacts, ...s.unstagedArtifacts },
        })),

      unstageArtifact: (artifactId) =>
        set((s) => {
          const draft = s.stagedArtifacts[artifactId];
          if (!draft) return s;
          const nextStaged = { ...s.stagedArtifacts };
          delete nextStaged[artifactId];
          return {
            stagedArtifacts: nextStaged,
            unstagedArtifacts: { ...s.unstagedArtifacts, [artifactId]: draft },
          };
        }),

      discardStagedArtifact: (artifactId) =>
        set((s) => {
          if (!(artifactId in s.stagedArtifacts)) return s;
          const next = { ...s.stagedArtifacts };
          delete next[artifactId];
          return { stagedArtifacts: next };
        }),

      clearArtifact: (artifactId) =>
        set((s) => {
          const unstaged = { ...s.unstagedArtifacts };
          const staged = { ...s.stagedArtifacts };
          delete unstaged[artifactId];
          delete staged[artifactId];
          return { unstagedArtifacts: unstaged, stagedArtifacts: staged };
        }),

      clearAll: () => set({ unstagedArtifacts: {}, stagedArtifacts: {} }),
    }),
    {
      name: 'aise-staging',
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
);
