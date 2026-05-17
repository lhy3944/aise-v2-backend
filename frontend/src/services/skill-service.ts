import { api } from '@/lib/api';
import type {
  SkillCreateRequest,
  SkillDraft,
  SkillListResponse,
  UserSkill,
} from '@/types/skills';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';
const BASE = '/api/v1/skills';

async function requestUpload(path: string, file: File): Promise<SkillDraft> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message =
      typeof payload?.detail === 'string'
        ? payload.detail
        : 'Markdown 파일을 읽지 못했습니다.';
    throw new Error(message);
  }

  return response.json();
}

export const skillService = {
  list: () => api.get<SkillListResponse>(BASE),

  previewGithub: (url: string) =>
    api.post<SkillDraft>(`${BASE}/preview/github`, { url }),

  previewText: (body: string, name?: string, description?: string) =>
    api.post<SkillDraft>(`${BASE}/preview/text`, { body, name, description }),

  previewUpload: (file: File) => requestUpload(`${BASE}/preview/upload`, file),

  create: (body: SkillCreateRequest) => api.post<UserSkill>(BASE, body),

  update: (
    id: string,
    body: Partial<Pick<UserSkill, 'name' | 'description' | 'body' | 'enabled'>>,
  ) => api.patch<UserSkill>(`${BASE}/${id}`, body),

  delete: (id: string) => api.delete<void>(`${BASE}/${id}`),
};
