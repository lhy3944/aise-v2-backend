import { api } from '@/lib/api';
import type {
  Record,
  RecordCreate,
  RecordExtractedItem,
  RecordListResponse,
  RecordStatus,
  RecordUpdate,
} from '@/types/project';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/records`;
}

export interface ExtractStreamEvent {
  type: 'progress' | 'done' | 'error';
  stage?: string;
  message?: string;
  candidates?: RecordExtractedItem[];
  status?: number;
}

export interface ExtractStreamHandlers {
  onProgress?: (stage: string | undefined, message: string | undefined) => void;
  onDone: (candidates: RecordExtractedItem[]) => void;
  onError: (message: string) => void;
}

/**
 * 레코드 추출 SSE 스트리밍 호출.
 * proxy keep-alive 타임아웃 회피를 위해 백엔드가 progress heartbeat를 보낸다.
 * @returns abort 함수
 */
export function streamExtractRecords(
  projectId: string,
  sectionId: string | undefined,
  handlers: ExtractStreamHandlers,
): () => void {
  const controller = new AbortController();
  const query = sectionId ? `?section_id=${sectionId}` : '';
  const url = `${API_BASE}${base(projectId)}/extract${query}`;

  (async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        handlers.onError(`서버 오류: ${response.status} ${errorText}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        handlers.onError('스트리밍을 시작할 수 없습니다.');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event: ExtractStreamEvent = JSON.parse(jsonStr);
            switch (event.type) {
              case 'progress':
                handlers.onProgress?.(event.stage, event.message);
                break;
              case 'done':
                handlers.onDone(event.candidates ?? []);
                return;
              case 'error':
                handlers.onError(event.message ?? '레코드 추출에 실패했습니다');
                return;
            }
          } catch {
            // JSON 파싱 실패 — 무시
          }
        }
      }
    } catch (err) {
      if (controller.signal.aborted) return;
      handlers.onError(err instanceof Error ? err.message : '네트워크 오류');
    }
  })();

  return () => controller.abort();
}

export const recordService = {
  list: (projectId: string, sectionId?: string) => {
    const query = sectionId ? `?section_id=${sectionId}` : '';
    return api.get<RecordListResponse>(`${base(projectId)}${query}`);
  },

  create: (projectId: string, data: RecordCreate) =>
    api.post<Record>(base(projectId), data),

  update: (projectId: string, recordId: string, data: RecordUpdate) =>
    api.put<Record>(`${base(projectId)}/${recordId}`, data),

  updateStatus: (projectId: string, recordId: string, status: RecordStatus) =>
    api.patch<Record>(`${base(projectId)}/${recordId}/status`, { status }),

  delete: (projectId: string, recordId: string) =>
    api.delete<void>(`${base(projectId)}/${recordId}`),

  reorder: (projectId: string, orderedIds: string[]) =>
    api.put<{ updated_count: number }>(`${base(projectId)}/reorder`, { ordered_ids: orderedIds }),

  /** 추출된 레코드 후보 일괄 승인 저장 */
  approve: (projectId: string, items: RecordCreate[]) =>
    api.post<RecordListResponse>(`${base(projectId)}/approve`, { items }),
};
