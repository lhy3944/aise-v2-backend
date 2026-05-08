'use client';

import { useEffect, useMemo, useState, useCallback } from 'react';

import { DiffViewer } from '@/components/artifacts/workspace/diff/DiffViewer';
import { ScrollArea } from '@/components/ui/scroll-area';
import { artifactService } from '@/services/artifact-service';
import { cn } from '@/lib/utils';
import type { ArtifactVersion } from '@/types/project';

interface RecordVersionsModalProps {
  projectId: string;
  artifactId: string;
  /** 카드 헤더에 표시할 컨텍스트 라벨 (예: "OVR-002"). */
  displayLabel?: string;
}

export function RecordVersionsModal({
  projectId,
  artifactId,
  displayLabel,
}: RecordVersionsModalProps) {
  const [versions, setVersions] = useState<ArtifactVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) setLoading(true);
    });
    artifactService
      .listVersions(projectId, artifactId)
      .then((res) => {
        if (cancelled) return;
        const sorted = [...res.versions].sort(
          (a, b) => b.version_number - a.version_number,
        );
        setVersions(sorted);
        setSelectedVersionId(sorted[0]?.version_id ?? null);
      })
      .catch(() => {
        if (!cancelled) return;
        setError('버전 히스토리를 불러오지 못했습니다.');
      })
      .finally(() => {
        if (!cancelled) return;
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, artifactId]);

  const selected = useMemo(
    () => versions.find((v) => v.version_id === selectedVersionId) ?? null,
    [versions, selectedVersionId],
  );

  const parent = useMemo(() => {
    if (!selected) return null;
    // 항상 한 단계 이전 버전 — 리스트는 최신→과거 순이므로 idx+1이 바로 직전 버전
    const idx = versions.findIndex((v) => v.version_id === selected.version_id);
    return idx >= 0 && idx + 1 < versions.length ? versions[idx + 1] : null;
  }, [versions, selected]);

  const handleVersionSelect = useCallback(
    (versionId: string) => {
      if (versionId === selectedVersionId) return;
      setSelectedVersionId(versionId);
    },
    [selectedVersionId],
  );

  if (error) {
    return <p className='text-destructive p-4 text-sm'>{error}</p>;
  }

  if (versions.length === 0) {
    return (
      <div className='flex h-64 flex-col items-center justify-center gap-2'>
        <p className='text-fg-secondary text-sm font-medium'>버전 없음</p>
        <p className='text-fg-muted text-xs'>
          이 산출물은 아직 머지된 버전이 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div className='flex h-[540px]'>
      {/* 좌측: version 리스트 */}
      <div className='border-line-primary flex w-48 shrink-0 flex-col border-r'>
        <div className='border-line-primary text-fg-muted border-b px-3 py-2 text-xs font-medium'>
          {displayLabel ?? '버전'} · {versions.length}개
        </div>
        <ScrollArea className='min-h-0 flex-1'>
          <div className='flex flex-col'>
            {versions.map((v, idx) => {
              const isSelected = v.version_id === selectedVersionId;
              const isLatest = idx === 0;
              return (
                <button
                  key={v.version_id}
                  type='button'
                  className={cn(
                    'relative text-left border-b py-2.5 pr-3 pl-4 transition-colors',
                    'border-line-primary',
                    isSelected ? 'bg-canvas-secondary' : 'hover:bg-canvas-secondary/30',
                  )}
                  onClick={() => handleVersionSelect(v.version_id)}
                >
                  {isSelected && (
                    <span className='absolute inset-y-0 left-0 w-0.5 bg-accent-primary' />
                  )}
                  <div className='flex items-center gap-2'>
                    <span className='text-fg-primary text-xs font-medium'>
                      v{v.version_number}
                    </span>
                    {isLatest && (
                      <span className='border-line-primary text-fg-muted rounded border px-1 py-px text-[10px]'>
                        최신
                      </span>
                    )}
                  </div>
                  <div className='text-fg-muted mt-1 text-[11px]'>
                    {new Date(v.committed_at).toLocaleString('ko-KR', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* 우측: diff */}
      <div className='min-w-0 flex-1'>
        <div className='flex h-full flex-col'>
          <div className='border-line-primary text-fg-muted border-b px-4 py-2 text-xs font-medium'>
            {selected
              ? parent
                ? `v${parent.version_number} → v${selected.version_number} 변경 내역`
                : `v${selected.version_number} (최초 버전)`
              : '버전을 선택하세요'}
          </div>
          <div className='min-h-0 flex-1 overflow-y-auto p-4'>
            {selected && (
              <DiffViewer
                headVersionId={selected.version_id}
                baseVersionId={parent?.version_id ?? null}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
