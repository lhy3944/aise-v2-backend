import { api } from '@/lib/api';
import type {
  ReviewRequest,
  ReviewResponse,
  LatestReviewResponse,
} from '@/types/project';

function base(projectId: string) {
  return `/api/v1/projects/${projectId}/review`;
}

export const reviewService = {
  /** 요구사항 리뷰 실행 (빈 배열이면 전체 리뷰) */
  review: (projectId: string, data: ReviewRequest) =>
    api.post<ReviewResponse>(`${base(projectId)}/requirements`, data),

  /** 마지막 리뷰 결과 조회 */
  getLatest: (projectId: string) =>
    api.get<LatestReviewResponse>(`${base(projectId)}/results/latest`),
};
