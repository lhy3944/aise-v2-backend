'use client';

import { FieldDiffRow } from '@/components/artifacts/workspace/diff/FieldDiffRow';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { artifactService } from '@/services/artifact-service';
import type { DiffFieldEntry, DiffResult } from '@/types/project';
import { useEffect, useMemo, useRef, useState } from 'react';

interface DiffViewerProps {
  headVersionId: string;
  baseVersionId?: string | null;
  /** 변경 없음 항목 기본 숨김 여부 (기본 true) */
  hideUnchanged?: boolean;
}

export function DiffViewer({
  headVersionId,
  baseVersionId,
  hideUnchanged = true,
}: DiffViewerProps) {
  const [data, setData] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUnchanged, setShowUnchanged] = useState(!hideUnchanged);

  const requestKey = `${headVersionId}::${baseVersionId ?? ''}`;
  const keyRef = useRef<string>('');

  useEffect(() => {
    let cancelled = false;
    keyRef.current = requestKey;
    setLoading(true);
    setError(null);
    setData(null);

    artifactService
      .diff(headVersionId, baseVersionId ?? undefined)
      .then((res) => {
        if (cancelled || keyRef.current !== requestKey) return;
        setData(res);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled || keyRef.current !== requestKey) return;
        setError(err instanceof Error ? err.message : 'diff 불러오기 실패');
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [headVersionId, baseVersionId, requestKey]);

  const { visibleEntries, counts } = useMemo(() => {
    const entries = data?.entries ?? [];
    const counts = {
      added: 0,
      removed: 0,
      modified: 0,
      unchanged: 0,
    };
    for (const e of entries) counts[e.kind] += 1;
    const visible = showUnchanged
      ? entries
      : entries.filter((e) => e.kind !== 'unchanged');
    return { visibleEntries: visible, counts };
  }, [data, showUnchanged]);

  if (loading) {
    return (
      <div className='flex h-40 items-center justify-center'>
        <Spinner size='size-5' className='text-fg-muted' />
      </div>
    );
  }

  if (error) {
    return (
      <div className='border-destructive/40 bg-destructive/5 text-destructive rounded-md border p-3 text-xs'>
        {error}
      </div>
    );
  }

  if (!data || data.entries.length === 0) {
    return (
      <p className='text-fg-muted p-3 text-center text-xs'>
        비교할 변경이 없습니다.
      </p>
    );
  }

  return (
    <div className='flex h-full min-h-0 flex-col gap-3'>
      <DiffHeader
        result={data}
        counts={counts}
        showUnchanged={showUnchanged}
        onToggleUnchanged={() => setShowUnchanged((v) => !v)}
      />
      <ScrollArea className='min-h-0 flex-1'>
        <div className='flex flex-col gap-2 pr-2'>
          {visibleEntries.length === 0 ? (
            <p className='text-fg-muted py-4 text-center text-xs'>
              표시할 변경이 없습니다. 변경 없음 항목을 표시해 보세요.
            </p>
          ) : (
            visibleEntries.map((entry) => (
              <FieldDiffRow key={entry.field_path} entry={entry} />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

interface DiffHeaderProps {
  result: DiffResult;
  counts: Record<DiffFieldEntry['kind'], number>;
  showUnchanged: boolean;
  onToggleUnchanged: () => void;
}

function DiffHeader({ result, counts, showUnchanged, onToggleUnchanged }: DiffHeaderProps) {
  const hasUnchanged = counts.unchanged > 0;
  return (
    <div className='border-line-primary bg-canvas-primary/40 flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-md border px-2.5 py-2'>
      <VersionChip label='base' value={result.base_version_id} />
      <span className='text-fg-muted text-[10px]'>→</span>
      <VersionChip label='head' value={result.head_version_id} />
      <div className='ml-auto flex items-center gap-2 text-[11px]'>
        <CountChip tone='emerald' count={counts.added} label='추가' />
        <CountChip tone='red' count={counts.removed} label='삭제' />
        <CountChip tone='amber' count={counts.modified} label='변경' />
        {hasUnchanged && (
          <button
            type='button'
            onClick={onToggleUnchanged}
            className='text-fg-muted hover:text-fg-secondary underline-offset-2 hover:underline'
          >
            {showUnchanged
              ? `변경 없음 숨기기 (${counts.unchanged})`
              : `변경 없음 표시 (${counts.unchanged})`}
          </button>
        )}
      </div>
    </div>
  );
}

function VersionChip({ label, value }: { label: string; value: string | null }) {
  return (
    <span className='text-fg-muted inline-flex items-center gap-1 font-mono text-[11px]'>
      <span className='uppercase opacity-70'>{label}</span>
      <span className='text-fg-secondary'>{value ? value.slice(0, 8) : '(없음)'}</span>
    </span>
  );
}

function CountChip({
  tone,
  count,
  label,
}: {
  tone: 'emerald' | 'red' | 'amber';
  count: number;
  label: string;
}) {
  const toneCls =
    tone === 'emerald'
      ? 'text-emerald-600'
      : tone === 'red'
        ? 'text-red-500'
        : 'text-amber-600';
  return (
    <span className={toneCls}>
      <span className='font-semibold tabular-nums'>{count}</span>
      <span className='text-fg-muted ml-1'>{label}</span>
    </span>
  );
}
