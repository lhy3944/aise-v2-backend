import { api } from '@/lib/api';
import type {
  GlossaryCreate,
  GlossaryExtractResponse,
  GlossaryGenerateResponse,
  GlossaryItem,
  GlossaryListResponse,
  GlossaryUpdate,
} from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/glossary`;
}

export const glossaryService = {
  list: (projectId: string) => api.get<GlossaryListResponse>(base(projectId)),

  create: (projectId: string, data: GlossaryCreate) =>
    api.post<GlossaryItem>(base(projectId), data),

  update: (projectId: string, glossaryId: string, data: GlossaryUpdate) =>
    api.put<GlossaryItem>(`${base(projectId)}/${glossaryId}`, data),

  delete: (projectId: string, glossaryId: string) =>
    api.delete<void>(`${base(projectId)}/${glossaryId}`),

  /** 요구사항 기반 자동 생성 (레거시) */
  generate: (projectId: string) =>
    api.post<GlossaryGenerateResponse>(`${base(projectId)}/generate`),

  /** 지식 문서 기반 용어 후보 추출 */
  extract: (projectId: string) =>
    api.post<GlossaryExtractResponse>(`${base(projectId)}/extract`),

  /** 추출된 후보 일괄 승인 저장 */
  approve: (projectId: string, items: GlossaryCreate[]) =>
    api.post<GlossaryListResponse>(`${base(projectId)}/approve`, { items }),
};
