import { api } from '@/lib/api';
import type {
  Project,
  ProjectCreate,
  ProjectDeletePreview,
  ProjectListResponse,
  ProjectSettings,
  ProjectSettingsUpdate,
  ProjectUpdate,
  ReadinessResponse,
} from '@/types/project';

const BASE = '/api/v1/projects';

export const projectService = {
  list: (includeDeleted = false) =>
    api.get<ProjectListResponse>(
      includeDeleted ? `${BASE}?include_deleted=true` : BASE,
    ),

  get: (id: string) => api.get<Project>(`${BASE}/${id}`),

  create: (data: ProjectCreate) => api.post<Project>(BASE, data),

  update: (id: string, data: ProjectUpdate) => api.put<Project>(`${BASE}/${id}`, data),

  /** soft delete — status='deleted' 마킹. 30일 retention 후 hard delete. */
  delete: (id: string, confirmName?: string) =>
    api.delete<void>(`${BASE}/${id}`, {
      body: confirmName ? { confirm_name: confirmName } : undefined,
    }),

  /** 삭제 시 영향받을 데이터 카운트 미리보기. */
  getDeletePreview: (id: string) =>
    api.get<ProjectDeletePreview>(`${BASE}/${id}/delete-preview`),

  /** soft-deleted 프로젝트 복원. */
  restore: (id: string) => api.post<Project>(`${BASE}/${id}/restore`),

  /** 영구 삭제 — DB CASCADE + MinIO prefix 정리. 복원 불가. */
  hardDelete: (id: string) => api.delete<void>(`${BASE}/${id}/hard`),

  getSettings: (id: string) => api.get<ProjectSettings>(`${BASE}/${id}/settings`),

  updateSettings: (id: string, data: ProjectSettingsUpdate) =>
    api.put<ProjectSettings>(`${BASE}/${id}/settings`, data),

  getReadiness: (id: string) => api.get<ReadinessResponse>(`${BASE}/${id}/readiness`),
};
