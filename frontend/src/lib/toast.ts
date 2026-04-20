import { toast } from 'sonner';

/**
 * 표준 Toast 헬퍼
 *
 * 사용법:
 *   showToast.success('저장되었습니다')
 *   showToast.error('저장에 실패했습니다', '네트워크 오류')
 *   showToast.info('처리 중입니다')
 *   showToast.warning('주의가 필요합니다')
 *   showToast.loading('저장 중...')
 *   showToast.promise(asyncFn(), { loading: '저장 중...', success: '완료', error: '실패' })
 *   showToast.dismiss(id)
 */
export const showToast = {
  success: (message: string, description?: string, id?: string | number) =>
    toast.success(message, { description, id }),

  error: (message: string, description?: string, id?: string | number) =>
    toast.error(message, { description, duration: 5000, id }),

  info: (message: string, description?: string, id?: string | number) =>
    toast.info(message, { description, id }),

  warning: (message: string, description?: string, id?: string | number) =>
    toast.warning(message, { description, duration: 5000, id }),

  loading: (message: string, id?: string | number) => toast.loading(message, { id }),

  promise: toast.promise,

  dismiss: toast.dismiss,
};
