import { api } from '@/lib/api';
import type { SrsDocument, SrsListResponse } from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/srs`;
}

export const srsService = {
  generate: (projectId: string) =>
    api.post<SrsDocument>(`${base(projectId)}/generate`),

  list: (projectId: string) =>
    api.get<SrsListResponse>(base(projectId)),

  get: (projectId: string, srsId: string) =>
    api.get<SrsDocument>(`${base(projectId)}/${srsId}`),

  updateSection: (projectId: string, srsId: string, sectionId: string, content: string) =>
    api.put<SrsDocument>(`${base(projectId)}/${srsId}/sections/${sectionId}`, { content }),

  regenerate: (projectId: string, srsId: string) =>
    api.post<SrsDocument>(`${base(projectId)}/${srsId}/regenerate`),
};
