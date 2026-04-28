import { api } from '@/lib/api';
import type {
  ImpactApplyRequest,
  ImpactApplyResponse,
  ImpactResponse,
} from '@/types/project';

export const impactService = {
  /** 프로젝트의 모든 stale artifact 목록. */
  get: (projectId: string) =>
    api.get<ImpactResponse>(`/api/v1/projects/${projectId}/impact`),

  /** 선택된(또는 전체) stale artifact 일괄 자동 재생성. */
  apply: (projectId: string, body: ImpactApplyRequest) =>
    api.post<ImpactApplyResponse>(
      `/api/v1/projects/${projectId}/impact/apply`,
      body,
    ),
};
