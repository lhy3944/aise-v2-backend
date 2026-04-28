import { api } from '@/lib/api';
import type { DesignDocument, DesignListResponse } from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/design`;
}

/**
 * Phase D: SRS 와 동일 패턴.
 * 사용자 수동 편집은 staging-store -> ChangesWorkspaceModal -> PR 워크플로우.
 */
export const designService = {
  generate: (projectId: string) =>
    api.post<DesignDocument>(`${base(projectId)}/generate`),

  list: (projectId: string) =>
    api.get<DesignListResponse>(base(projectId)),

  get: (projectId: string, designId: string) =>
    api.get<DesignDocument>(`${base(projectId)}/${designId}`),

  regenerate: (projectId: string, designId: string) =>
    api.post<DesignDocument>(`${base(projectId)}/${designId}/regenerate`),
};
