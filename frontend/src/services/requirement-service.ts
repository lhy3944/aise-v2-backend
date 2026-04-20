import { api } from '@/lib/api';
import type {
  Requirement,
  RequirementCreate,
  RequirementListResponse,
  RequirementReorderRequest,
  RequirementSaveResponse,
  RequirementSelectionUpdate,
  RequirementType,
  RequirementUpdate,
} from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/requirements`;
}

export const requirementService = {
  list: (projectId: string, type?: RequirementType) => {
    const query = type ? `?type=${type}` : '';
    return api.get<RequirementListResponse>(`${base(projectId)}${query}`);
  },

  create: (projectId: string, data: RequirementCreate) =>
    api.post<Requirement>(base(projectId), data),

  update: (projectId: string, requirementId: string, data: RequirementUpdate) =>
    api.put<Requirement>(`${base(projectId)}/${requirementId}`, data),

  delete: (projectId: string, requirementId: string) =>
    api.delete<void>(`${base(projectId)}/${requirementId}`),

  updateSelection: (projectId: string, data: RequirementSelectionUpdate) =>
    api.put<void>(`${base(projectId)}/selection`, data),

  reorder: (projectId: string, data: RequirementReorderRequest) =>
    api.put<{ updated_count: number }>(`${base(projectId)}/reorder`, data),

  save: (projectId: string) => api.post<RequirementSaveResponse>(`${base(projectId)}/save`),
};
