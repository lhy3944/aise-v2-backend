import useSWR, { type SWRConfiguration } from 'swr';
import { api, ApiError } from '@/lib/api';

/**
 * SWR 기반 GET 데이터 페칭 훅
 *
 * 사용법:
 *   const { data, error, isLoading, mutate } = useFetch<ProjectListResponse>('/api/v1/projects');
 *   const { data } = useFetch<Project>(projectId ? `/api/v1/projects/${projectId}` : null);
 *
 * - key가 null이면 요청을 건너뜀 (조건부 페칭)
 * - 에러는 ApiError 타입
 * - mutate()로 수동 재검증 가능
 */
export function useFetch<T>(key: string | null, config?: SWRConfiguration<T, ApiError>) {
  return useSWR<T, ApiError>(
    key,
    (path: string) => api.get<T>(path),
    {
      revalidateOnFocus: false,
      ...config,
    },
  );
}
