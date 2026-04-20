import type { ErrorResponse } from '@/types/project';

// 프로덕션/프리뷰: 빈 문자열 → 같은 도메인으로 요청 → Next.js rewrites가 백엔드로 프록시
// 로컬 개발: NEXT_PUBLIC_API_URL=http://localhost:8081 직접 호출
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export class ApiError extends Error {
  code: string;
  status: number;
  detail?: string | null;

  constructor(status: number, error: ErrorResponse['error']) {
    super(error.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = error.code;
    this.detail = error.detail;
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** true면 글로벌 에러 핸들링을 건너뛴다 (호출자가 직접 처리) */
  skipErrorHandling?: boolean;
}

async function handleGlobalError(error: ApiError): Promise<void> {
  if (typeof window === 'undefined') return;

  if (error.status === 401) {
    // 인증 만료 — 로그인 페이지로 리다이렉트
    window.location.href = '/login';
    return;
  }

  // 글로벌 에러 토스트 (동적 import로 서버 사이드 안전)
  const { showToast } = await import('@/lib/toast');

  const toastId = `api-error-${error.status}-${error.code}`;

  if (error.status >= 500) {
    showToast.error('서버 오류가 발생했습니다', error.detail ?? error.message, toastId);
  } else if (error.status >= 400) {
    showToast.error(error.message, error.detail ?? undefined, toastId);
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers: customHeaders, skipErrorHandling, ...rest } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(customHeaders as Record<string, string>),
  };

  const config: RequestInit = {
    ...rest,
    headers,
  };

  if (body !== undefined) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path}`, config);

  if (!response.ok) {
    let errorInfo: ErrorResponse['error'] = {
      code: 'UNKNOWN_ERROR',
      message: response.statusText || '알 수 없는 오류가 발생했습니다',
    };

    try {
      const body = await response.json();
      if (body?.error?.message) {
        errorInfo = body.error;
      } else if (body?.detail) {
        errorInfo = { code: 'API_ERROR', message: body.detail };
      } else if (body?.message) {
        errorInfo = { code: 'API_ERROR', message: body.message };
      }
    } catch {
      // JSON 파싱 실패 — 기본 errorInfo 사용
    }

    const apiError = new ApiError(response.status, errorInfo);

    if (!skipErrorHandling) {
      await handleGlobalError(apiError);
    }

    throw apiError;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { method: 'GET', ...options }),

  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { method: 'POST', body, ...options }),

  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { method: 'PUT', body, ...options }),

  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { method: 'PATCH', body, ...options }),

  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { method: 'DELETE', ...options }),
};
