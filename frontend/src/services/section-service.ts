import { api } from '@/lib/api';
import type {
  Section,
  SectionCreate,
  SectionListResponse,
  SectionReorderRequest,
  SectionUpdate,
} from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/requirement-sections`;
}

export const sectionService = {
  list: (projectId: string, type?: string) => {
    const query = type ? `?type=${type}` : '';
    return api.get<SectionListResponse>(`${base(projectId)}${query}`);
  },

  create: (projectId: string, data: SectionCreate) => api.post<Section>(base(projectId), data),

  update: (projectId: string, sectionId: string, data: SectionUpdate) =>
    api.put<Section>(`${base(projectId)}/${sectionId}`, data),

  toggle: (projectId: string, sectionId: string, isActive: boolean) =>
    api.patch<Section>(`${base(projectId)}/${sectionId}/toggle`, { is_active: isActive }),

  delete: (projectId: string, sectionId: string) =>
    api.delete<void>(`${base(projectId)}/${sectionId}`),

  reorder: (projectId: string, data: SectionReorderRequest) =>
    api.put<{ updated_count: number }>(`${base(projectId)}/reorder`, data),

  /** 지식 문서 기반 섹션 후보 AI 추출 */
  extract: (projectId: string) =>
    api.post<SectionListResponse>(`${base(projectId)}/extract`),
};
