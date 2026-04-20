import { useCallback, useState } from 'react';
import { ApiError } from '@/lib/api';
import { showToast } from '@/lib/toast';

interface MutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  onSuccess?: (data: TData) => void;
  onError?: (error: ApiError) => void;
  /** 성공 시 자동 toast 메시지 (falsy면 표시 안 함) */
  successMessage?: string;
  /** 에러 시 자동 toast 메시지 (falsy면 표시 안 함, 기본: 에러 메시지 표시) */
  errorMessage?: string | false;
}

interface MutationResult<TData, TVariables> {
  mutate: (variables: TVariables) => Promise<TData | undefined>;
  isLoading: boolean;
  error: ApiError | null;
  data: TData | null;
  reset: () => void;
}

/**
 * 표준 mutation 훅
 *
 * 사용법:
 *   const { mutate, isLoading } = useMutation({
 *     mutationFn: (data: ProjectCreate) => projectService.create(data),
 *     successMessage: '프로젝트가 생성되었습니다',
 *     onSuccess: () => router.push('/projects'),
 *   });
 */
export function useMutation<TData = unknown, TVariables = void>(
  options: MutationOptions<TData, TVariables>,
): MutationResult<TData, TVariables> {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [data, setData] = useState<TData | null>(null);

  const mutate = useCallback(
    async (variables: TVariables): Promise<TData | undefined> => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await options.mutationFn(variables);
        setData(result);

        if (options.successMessage) {
          showToast.success(options.successMessage);
        }

        options.onSuccess?.(result);
        return result;
      } catch (err) {
        const apiError = err instanceof ApiError ? err : new ApiError(0, {
          code: 'UNKNOWN_ERROR',
          message: err instanceof Error ? err.message : 'Unknown error',
        });

        setError(apiError);

        if (options.errorMessage !== false) {
          showToast.error(options.errorMessage ?? apiError.message);
        }

        options.onError?.(apiError);
        return undefined;
      } finally {
        setIsLoading(false);
      }
    },
    [options],
  );

  const reset = useCallback(() => {
    setIsLoading(false);
    setError(null);
    setData(null);
  }, []);

  return { mutate, isLoading, error, data, reset };
}
