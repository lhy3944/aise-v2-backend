'use client';

import { ApiError } from '@/lib/api';
import { showToast } from '@/lib/toast';
import { reviewService } from '@/services/review-service';
import type { LatestReviewResponse, ReviewResponse } from '@/types/project';
import { useState } from 'react';

interface UseReviewOptions {
  projectId: string;
}

export function useReview({ projectId }: UseReviewOptions) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [reviewData, setReviewData] = useState<ReviewResponse | LatestReviewResponse | null>(null);
  const [isReviewing, setIsReviewing] = useState(false);

  /** Review execution (empty array = full review) */
  const runReview = async (requirementIds: string[] = []) => {
    setIsModalOpen(true);
    setIsReviewing(true);
    setReviewData(null);
    try {
      const result = await reviewService.review(projectId, { requirement_ids: requirementIds });
      setReviewData(result);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '리뷰 실행에 실패했습니다.';
      showToast.error(msg);
      setIsModalOpen(false);
    } finally {
      setIsReviewing(false);
    }
  };

  /** Load latest review result */
  const loadLatest = async () => {
    setIsModalOpen(true);
    setIsReviewing(true);
    setReviewData(null);
    try {
      const result = await reviewService.getLatest(projectId);
      setReviewData(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setReviewData(null);
      } else {
        const msg = err instanceof ApiError ? err.message : '리뷰 결과를 불러올 수 없습니다.';
        showToast.error(msg);
        setIsModalOpen(false);
      }
    } finally {
      setIsReviewing(false);
    }
  };

  return {
    isModalOpen,
    setIsModalOpen,
    reviewData,
    isReviewing,
    runReview,
    // loadLatest — v2에서 "이전 결과" UI 추가 시 복원
  };
}
