import { api } from '@/lib/api';
import type {
  KnowledgeDocument,
  KnowledgeDocumentListResponse,
  KnowledgeDocumentPreview,
} from '@/types/project';

const BASE = '/api/v1/projects';

export const knowledgeService = {
  list: (projectId: string) =>
    api.get<KnowledgeDocumentListResponse>(`${BASE}/${projectId}/knowledge/documents`),

  get: (projectId: string, documentId: string) =>
    api.get<KnowledgeDocument>(`${BASE}/${projectId}/knowledge/documents/${documentId}`),

  uploadText: async (projectId: string, title: string, content: string, overwrite = false, fileType: 'txt' | 'md' = 'txt') => {
    const mimeType = fileType === 'md' ? 'text/markdown' : 'text/plain';
    const ext = fileType === 'md' ? '.md' : '.txt';
    const blob = new Blob([content], { type: mimeType });
    const fileName = title.endsWith(ext) ? title : `${title}${ext}`;
    const file = new File([blob], fileName, { type: mimeType });

    return knowledgeService.upload(projectId, file, overwrite);
  },

  upload: async (projectId: string, file: File, overwrite = false) => {
    const formData = new FormData();
    formData.append('file', file);

    const url = `${BASE}/${projectId}/knowledge/documents?overwrite=${overwrite}`;
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? ''}${url}`,
      { method: 'POST', body: formData },
    );

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const message = body?.error?.message ?? body?.detail ?? '업로드 실패';
      const error = new Error(message) as Error & { status: number };
      error.status = response.status;
      throw error;
    }

    return response.json() as Promise<KnowledgeDocument>;
  },

  toggle: (projectId: string, documentId: string, isActive: boolean) =>
    api.patch<KnowledgeDocument>(
      `${BASE}/${projectId}/knowledge/documents/${documentId}/toggle`,
      { is_active: isActive },
    ),

  preview: (projectId: string, documentId: string) =>
    api.get<KnowledgeDocumentPreview>(
      `${BASE}/${projectId}/knowledge/documents/${documentId}/preview`,
    ),

  reprocess: (projectId: string, documentId: string) =>
    api.post<KnowledgeDocument>(
      `${BASE}/${projectId}/knowledge/documents/${documentId}/reprocess`,
    ),

  delete: (projectId: string, documentId: string) =>
    api.delete<void>(`${BASE}/${projectId}/knowledge/documents/${documentId}`),
};
