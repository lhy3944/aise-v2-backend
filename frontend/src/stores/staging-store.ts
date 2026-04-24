'use client';

import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

/**
 * 로컬 편집 드래프트 — Unstaged / Staged 2단계, **프로젝트 네임스페이스**.
 *
 * plan §2.3 에 따라 staging-store 는 서버 상태가 아닌 UI 버퍼 전용.
 * 서버 호출 전까지 새로고침 방어 + 프로젝트 전환 후 복귀해도 작업을 이어갈
 * 수 있도록 sessionStorage 에 projectId 별로 bucket 보관.
 *
 * 상태 전이 (projectId 스코프 내):
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

interface ProjectBucket {
  unstaged: { [artifactId: string]: ArtifactDraft };
  staged: { [artifactId: string]: ArtifactDraft };
}

/** 빈 bucket 싱글턴 — selector 참조 안정성 유지 (새 객체 생성 방지 → 리렌더 방지). */
export const EMPTY_BUCKET: ProjectBucket = Object.freeze({
  unstaged: Object.freeze({}) as ProjectBucket['unstaged'],
  staged: Object.freeze({}) as ProjectBucket['staged'],
}) as ProjectBucket;

interface StagingState {
  byProject: { [projectId: string]: ProjectBucket };

  // Unstaged CRUD
  setDraft: (projectId: string, draft: ArtifactDraft) => void;
  discardDraft: (projectId: string, artifactId: string) => void;

  // Stage 전이
  stage: (projectId: string, artifactId: string) => void;
  stageAll: (projectId: string) => void;
  unstage: (projectId: string, artifactId: string) => void;

  // Staged CRUD
  discardStaged: (projectId: string, artifactId: string) => void;

  // 서버 반영 완료 — 해당 artifact 의 양쪽 드래프트 모두 제거
  clearArtifact: (projectId: string, artifactId: string) => void;

  // 프로젝트 전체 초기화 (명시적 호출용. 프로젝트 전환 시에는 쓰지 않는다 —
  // 사용자의 다른 프로젝트 작업을 이어가기 위해 bucket 은 보존.)
  clearProject: (projectId: string) => void;
}

function bucketOf(
  state: StagingState,
  projectId: string,
): ProjectBucket {
  return state.byProject[projectId] ?? EMPTY_BUCKET;
}

export const useStagingStore = create<StagingState>()(
  persist(
    (set) => ({
      byProject: {},

      setDraft: (projectId, draft) =>
        set((s) => {
          const current = bucketOf(s, projectId);
          return {
            byProject: {
              ...s.byProject,
              [projectId]: {
                unstaged: { ...current.unstaged, [draft.artifactId]: draft },
                staged: current.staged,
              },
            },
          };
        }),

      discardDraft: (projectId, artifactId) =>
        set((s) => {
          const current = bucketOf(s, projectId);
          if (!(artifactId in current.unstaged)) return s;
          const nextUnstaged = { ...current.unstaged };
          delete nextUnstaged[artifactId];
          return {
            byProject: {
              ...s.byProject,
              [projectId]: { unstaged: nextUnstaged, staged: current.staged },
            },
          };
        }),

      stage: (projectId, artifactId) =>
        set((s) => {
          const current = bucketOf(s, projectId);
          const draft = current.unstaged[artifactId];
          if (!draft) return s;
          const nextUnstaged = { ...current.unstaged };
          delete nextUnstaged[artifactId];
          return {
            byProject: {
              ...s.byProject,
              [projectId]: {
                unstaged: nextUnstaged,
                staged: { ...current.staged, [artifactId]: draft },
              },
            },
          };
        }),

      stageAll: (projectId) =>
        set((s) => {
          const current = bucketOf(s, projectId);
          return {
            byProject: {
              ...s.byProject,
              [projectId]: {
                unstaged: {},
                staged: { ...current.staged, ...current.unstaged },
              },
            },
          };
        }),

      unstage: (projectId, artifactId) =>
        set((s) => {
          const current = bucketOf(s, projectId);
          const draft = current.staged[artifactId];
          if (!draft) return s;
          const nextStaged = { ...current.staged };
          delete nextStaged[artifactId];
          return {
            byProject: {
              ...s.byProject,
              [projectId]: {
                staged: nextStaged,
                unstaged: { ...current.unstaged, [artifactId]: draft },
              },
            },
          };
        }),

      discardStaged: (projectId, artifactId) =>
        set((s) => {
          const current = bucketOf(s, projectId);
          if (!(artifactId in current.staged)) return s;
          const nextStaged = { ...current.staged };
          delete nextStaged[artifactId];
          return {
            byProject: {
              ...s.byProject,
              [projectId]: { staged: nextStaged, unstaged: current.unstaged },
            },
          };
        }),

      clearArtifact: (projectId, artifactId) =>
        set((s) => {
          const current = bucketOf(s, projectId);
          const unstaged = { ...current.unstaged };
          const staged = { ...current.staged };
          delete unstaged[artifactId];
          delete staged[artifactId];
          return {
            byProject: {
              ...s.byProject,
              [projectId]: { unstaged, staged },
            },
          };
        }),

      clearProject: (projectId) =>
        set((s) => {
          if (!(projectId in s.byProject)) return s;
          const next = { ...s.byProject };
          delete next[projectId];
          return { byProject: next };
        }),
    }),
    {
      name: 'aise-staging',
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
);

// ── Selector 헬퍼 ───────────────────────────────────────────────────────────
// 컴포넌트 리렌더 최소화를 위해 개별 필드 selector 사용을 권장.
// 예:
//   const unstaged = useStagingStore((s) => s.byProject[projectId]?.unstaged ?? EMPTY_BUCKET.unstaged);
