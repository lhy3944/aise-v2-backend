import { api } from '@/lib/api';
import type {
  ChatRequest,
  ChatResponse,
  RefineRequest,
  RefineResponse,
  SuggestRequest,
  SuggestResponse,
} from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/assist`;
}

export const assistService = {
  refine: (projectId: string, data: RefineRequest) =>
    api.post<RefineResponse>(`${base(projectId)}/refine`, data),

  suggest: (projectId: string, data: SuggestRequest) =>
    api.post<SuggestResponse>(`${base(projectId)}/suggest`, data),

  chat: (projectId: string, data: ChatRequest) =>
    api.post<ChatResponse>(`${base(projectId)}/chat`, data),
};
