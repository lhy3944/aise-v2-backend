/**
 * Session API 서비스
 */

import { api } from '@/lib/api';

export interface SessionResponse {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionMessageResponse {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_calls: Array<{
    name: string;
    arguments: Record<string, unknown>;
    /** tool_result에서 매칭된 값 — 없을 수도 있음 */
    status?: 'success' | 'error';
    duration_ms?: number;
    result?: Record<string, unknown> | null;
  }> | null;
  tool_data: Record<string, unknown> | null;
  created_at: string;
}

export interface SessionDetailResponse extends SessionResponse {
  messages: SessionMessageResponse[];
}

export interface SessionListResponse {
  sessions: SessionResponse[];
}

export const sessionService = {
  create: (projectId: string, title?: string) =>
    api.post<SessionResponse>('/api/v1/sessions', {
      project_id: projectId,
      title,
    }),

  list: (projectId: string) =>
    api.get<SessionListResponse>(`/api/v1/sessions?project_id=${projectId}`),

  get: (sessionId: string) =>
    api.get<SessionDetailResponse>(`/api/v1/sessions/${sessionId}`),

  update: (sessionId: string, title: string) =>
    api.patch<SessionResponse>(`/api/v1/sessions/${sessionId}`, { title }),

  delete: (sessionId: string) =>
    api.delete<void>(`/api/v1/sessions/${sessionId}`),
};
