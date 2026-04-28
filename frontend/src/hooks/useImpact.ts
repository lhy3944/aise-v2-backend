'use client';

import { useEffect, useState } from 'react';

import { impactService } from '@/services/impact-service';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import type { ImpactedArtifact } from '@/types/project';

/**
 * 프로젝트의 stale artifact 목록을 구독.
 *
 * artifact-refresh-store.bumpAll() 이 호출될 때마다(=PR 머지 등) 재조회한다.
 * 한 번 fetch 한 결과는 ImpactedArtifact[] 로 보관되며, 호출자는
 * `staleByArtifactId[artifactId]` 로 O(1) 조회한다.
 */
export function useImpact(projectId: string | null | undefined): {
  stale: ImpactedArtifact[];
  staleByArtifactId: Record<string, ImpactedArtifact>;
  loading: boolean;
} {
  const [stale, setStale] = useState<ImpactedArtifact[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // SRS/Design/TC/Record 어느 쪽이라도 머지가 발생하면 lineage 가 흔들리므로
  // bump nonce 의 합으로 trigger.
  const nonceRecord = useArtifactRefreshStore((s) => s.nonce.record);
  const nonceSrs = useArtifactRefreshStore((s) => s.nonce.srs);
  const nonceDesign = useArtifactRefreshStore((s) => s.nonce.design);
  const nonceTestcase = useArtifactRefreshStore((s) => s.nonce.testcase);
  const trigger = nonceRecord + nonceSrs + nonceDesign + nonceTestcase;

  useEffect(() => {
    if (!projectId) {
      setStale([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    impactService
      .get(projectId)
      .then((res) => {
        if (cancelled) return;
        setStale(res.stale);
      })
      .catch(() => {
        if (cancelled) return;
        setStale([]);
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, trigger]);

  const staleByArtifactId: Record<string, ImpactedArtifact> = {};
  for (const item of stale) staleByArtifactId[item.artifact_id] = item;

  return { stale, staleByArtifactId, loading };
}
