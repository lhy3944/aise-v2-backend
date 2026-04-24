'use client';

import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { usePrStore } from '@/stores/pr-store';
import { useProjectStore } from '@/stores/project-store';
import { useRouter } from 'next/navigation';
import { useEffect, useRef } from 'react';

/**
 * 프로젝트 전환 감지 훅.
 *
 * - 프로젝트가 실제로 바뀌는 시점에만 동작 (최초 마운트 포함 자동 무시).
 * - 프로젝트별로 보존해야 하는 상태(staging-store 의 drafts)는 그대로 두고,
 *   프로젝트 간 공유가 불가한 서버 캐시·임시 상태만 리셋:
 *     • pr-store.openPRs       — 재조회로 복원됨
 *     • artifact-record-store  — candidates / extractError 는 1회성 추출 결과
 * - 중앙 패널이 이전 프로젝트의 세션을 계속 렌더하지 않도록
 *   router.push('/agent') 로 세션 없는 초기 화면으로 이동.
 *
 * 호출 위치: `(main)/agent/layout.tsx` — 이 경로에 들어온 이후에만 전환을
 * 감지하면 충분. projects/[id] 등 다른 라우트는 URL 자체가 바뀌므로 불필요.
 */
export function useProjectScopedReset() {
  const projectId =
    useProjectStore((s) => s.currentProject?.project_id) ?? null;
  const prevRef = useRef<string | null>(projectId);
  const router = useRouter();

  useEffect(() => {
    const prev = prevRef.current;
    prevRef.current = projectId;

    // 최초 마운트(prev=null) 또는 값 동일 시 아무 것도 안 함
    if (prev === null || prev === projectId) return;

    // 서버 캐시 리셋 → 새 프로젝트 로드 시 재조회
    usePrStore.getState().reset();
    useArtifactRecordStore.getState().clearCandidates();

    // 중앙 패널이 이전 세션 메시지를 계속 보여주지 않도록 세션 없는 경로로
    router.push('/agent');
  }, [projectId, router]);
}
