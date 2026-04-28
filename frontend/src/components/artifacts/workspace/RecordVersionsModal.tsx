'use client';

import { ChevronRight, History, Loader2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

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

/**
 * record(또는 임의 artifact)의 모든 ArtifactVersion 히스토리 + diff 모달 본문.
 * - 좌측: version selector 리스트 (최신 → 과거 순)
 * - 우측: 선택된 version vs 그 이전 version 의 DiffViewer
 *
 * SRS/Design 화면의 selectbox 대신 list 형태 — record 는 카드 단위라 별도 화면이
 * 없어 모달 안에서 selector 가 더 명확하다.
 */
export function RecordVersionsModal({
  projectId,
  artifactId,
  displayLabel,
}: RecordVersionsModalProps) {
  const [versions, setVersions] = useState<ArtifactVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
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
        if (cancelled) return;
        setError('버전 히스토리를 불러오지 못했습니다.');
      })
      .finally(() => {
        if (cancelled) return;
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

  // 선택된 version 의 직전 version (parent) — diff base
  const parent = useMemo(() => {
    if (!selected) return null;
    if (selected.parent_version_id) {
      return (
        versions.find((v) => v.version_id === selected.parent_version_id) ??
        null
      );
    }
    // parent_version_id 가 없으면 list 에서 직전 version 찾기
    const idx = versions.findIndex((v) => v.version_id === selected.version_id);
    return idx >= 0 && idx + 1 < versions.length ? versions[idx + 1] : null;
  }, [versions, selected]);

  if (loading) {
    return (
      <div className='text-fg-muted flex h-32 items-center justify-center text-xs'>
        <Loader2 className='mr-2 size-4 animate-spin' />
        버전 히스토리 로드 중...
      </div>
    );
  }
  if (error) {
    return <p className='text-destructive text-xs'>{error}</p>;
  }
  if (versions.length === 0) {
    return (
      <div className='flex h-32 flex-col items-center justify-center gap-2 text-center'>
        <History className='text-fg-muted size-8' />
        <p className='text-fg-secondary text-sm font-medium'>버전 없음</p>
        <p className='text-fg-muted text-xs'>
          이 산출물은 아직 한 번도 머지되지 않아 버전이 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div className='flex max-h-[60vh] min-h-0 gap-3'>
      {/* 좌측: version 리스트 */}
      <div className='border-line-primary flex w-44 shrink-0 flex-col rounded-md border'>
        <div className='border-line-primary text-fg-muted flex items-center gap-1.5 border-b px-2.5 py-1.5 text-[11px] font-semibold tracking-wider uppercase'>
          <History className='size-3' />
          버전 ({versions.length}){displayLabel && ` · ${displayLabel}`}
        </div>
        <ScrollArea className='min-h-0 flex-1'>
          <ul>
            {versions.map((v, idx) => {
              const isSelected = v.version_id === selectedVersionId;
              const isLatest = idx === 0;
              return (
                <li
                  key={v.version_id}
                  className={cn(
                    'border-line-primary/60 hover:bg-canvas-primary/40 cursor-pointer border-b px-2.5 py-2 text-xs last:border-b-0',
                    isSelected && 'bg-canvas-primary/60',
                  )}
                  onClick={() => setSelectedVersionId(v.version_id)}
                >
                  <div className='flex items-center gap-1.5'>
                    <span className='text-fg-primary font-mono font-medium'>
                      v{v.version_number}
                    </span>
                    {isLatest && (
                      <span className='bg-muted text-fg-muted rounded px-1.5 py-0.5 text-[9px]'>
                        latest
                      </span>
                    )}
                    <ChevronRight
                      className={cn(
                        'text-fg-muted ml-auto size-3 transition-opacity',
                        isSelected ? 'opacity-100' : 'opacity-0',
                      )}
                    />
                  </div>
                  <div className='text-fg-muted mt-0.5 text-[10px]'>
                    {new Date(v.committed_at).toLocaleString('ko-KR', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </div>
                  {v.commit_message && (
                    <div className='text-fg-secondary mt-0.5 line-clamp-2 text-[11px]'>
                      {v.commit_message}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </ScrollArea>
      </div>

      {/* 우측: diff */}
      <div className='border-line-primary min-w-0 flex-1 rounded-md border'>
        <div className='border-line-primary text-fg-muted border-b px-3 py-1.5 text-[11px] font-semibold'>
          {selected
            ? parent
              ? `v${parent.version_number} → v${selected.version_number} 변경 내역`
              : `v${selected.version_number} (최초 버전)`
            : '버전을 선택하세요'}
        </div>
        <div className='min-h-0 flex-1 overflow-hidden'>
          {selected && (
            <DiffViewer
              headVersionId={selected.version_id}
              baseVersionId={parent?.version_id ?? null}
            />
          )}
        </div>
      </div>
    </div>
  );
}
