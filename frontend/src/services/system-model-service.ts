import { api } from '@/lib/api';
import type {
  SystemModelDocument,
  SystemModelListResponse,
} from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/system-model`;
}

export const systemModelService = {
  generate: (projectId: string) =>
    api.post<SystemModelDocument>(`${base(projectId)}/generate`),

  list: (projectId: string) =>
    api.get<SystemModelListResponse>(base(projectId)),

  get: (projectId: string, systemModelId: string) =>
    api.get<SystemModelDocument>(`${base(projectId)}/${systemModelId}`),

  regenerate: (projectId: string, systemModelId: string) =>
    api.post<SystemModelDocument>(`${base(projectId)}/${systemModelId}/regenerate`),
};
