import { api } from '@/lib/api';
import type {
  DataModelDocument,
  DataModelListResponse,
} from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/data-model`;
}

export const dataModelService = {
  generate: (projectId: string) =>
    api.post<DataModelDocument>(`${base(projectId)}/generate`),

  list: (projectId: string) =>
    api.get<DataModelListResponse>(base(projectId)),

  get: (projectId: string, dataModelId: string) =>
    api.get<DataModelDocument>(`${base(projectId)}/${dataModelId}`),

  regenerate: (projectId: string, dataModelId: string) =>
    api.post<DataModelDocument>(`${base(projectId)}/${dataModelId}/regenerate`),
};
