import { api } from '@/lib/api';
import type { SrsDocument, SrsListResponse } from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/srs`;
}

/**
 * Phase C 변경: SRS 섹션 인라인 편집(`updateSection`) 제거.
 * 사용자 수동 편집은 staging-store -> ChangesWorkspaceModal -> PR 워크플로우로
 * 통일 (artifactService.update + createPR + mergePR).
 */
export const srsService = {
  generate: (projectId: string) =>
    api.post<SrsDocument>(`${base(projectId)}/generate`),

  list: (projectId: string) =>
    api.get<SrsListResponse>(base(projectId)),

  get: (projectId: string, srsId: string) =>
    api.get<SrsDocument>(`${base(projectId)}/${srsId}`),

  regenerate: (projectId: string, srsId: string) =>
    api.post<SrsDocument>(`${base(projectId)}/${srsId}/regenerate`),
};
