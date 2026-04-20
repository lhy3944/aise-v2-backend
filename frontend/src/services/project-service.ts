import { api } from '@/lib/api';
import type {
  Project,
  ProjectCreate,
  ProjectListResponse,
  ProjectSettings,
  ProjectSettingsUpdate,
  ProjectUpdate,
  ReadinessResponse,
} from '@/types/project';

const BASE = '/api/v1/projects';

export const projectService = {
  list: () => api.get<ProjectListResponse>(BASE),

  get: (id: string) => api.get<Project>(`${BASE}/${id}`),

  create: (data: ProjectCreate) => api.post<Project>(BASE, data),

  update: (id: string, data: ProjectUpdate) => api.put<Project>(`${BASE}/${id}`, data),

  delete: (id: string) => api.delete<void>(`${BASE}/${id}`),

  getSettings: (id: string) => api.get<ProjectSettings>(`${BASE}/${id}/settings`),

  updateSettings: (id: string, data: ProjectSettingsUpdate) =>
    api.put<ProjectSettings>(`${BASE}/${id}/settings`, data),

  getReadiness: (id: string) => api.get<ReadinessResponse>(`${BASE}/${id}/readiness`),
};
