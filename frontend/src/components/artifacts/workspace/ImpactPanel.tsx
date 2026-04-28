'use client';

import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileText,
  FlaskConical,
  Layers,
  Loader2,
  XCircle,
} from 'lucide-react';
import { useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useImpact } from '@/hooks/useImpact';
import { cn } from '@/lib/utils';
import { impactService } from '@/services/impact-service';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import type { ImpactedArtifact, ImpactApplyResponse } from '@/types/project';

const KIND_ICON: Record<string, typeof Database> = {
  record: Database,
  srs: FileText,
  design: Layers,
  testcase: FlaskConical,
};

const AUTO_REGENERATABLE = new Set(['srs', 'design']);

interface ImpactPanelProps {
  projectId: string;
  onClose?: () => void;
}

export function ImpactPanel({ projectId, onClose }: ImpactPanelProps) {
  const { stale, loading } = useImpact(projectId);
  const bumpAll = useArtifactRefreshStore((s) => s.bumpAll);

  // 선택된 artifact_id set
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [applying, setApplying] = useState(false);
  const [result, setResult] = useState<ImpactApplyResponse | null>(null);

  // 자동 재생성 가능한 stale 만 기본으로 선택
  const autoRegenIds = useMemo(
    () =>
      stale
        .filter((s) => AUTO_REGENERATABLE.has(s.artifact_type))
        .map((s) => s.artifact_id),
    [stale],
  );

  const allSelected =
    autoRegenIds.length > 0 && autoRegenIds.every((id) => selected.has(id));

  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(autoRegenIds));
  };

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleApply = async () => {
    if (selected.size === 0) return;
    setApplying(true);
    setResult(null);
    try {
      const res = await impactService.apply(projectId, {
        artifact_ids: Array.from(selected),
      });
      setResult(res);
      // 새 ArtifactVersion 이 생겼으니 모든 화면 새로고침 트리거
      bumpAll();
      setSelected(new Set());
    } catch {
      // 글로벌 핸들링
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className='text-fg-muted flex h-32 items-center justify-center text-xs'>
        <Loader2 className='mr-2 size-4 animate-spin' />
        영향도 분석 중...
      </div>
    );
  }

  if (stale.length === 0 && !result) {
    return (
      <div className='flex h-32 flex-col items-center justify-center gap-2 text-center'>
        <CheckCircle2 className='size-8 text-emerald-500' />
        <p className='text-fg-secondary text-sm font-medium'>모두 최신 상태</p>
        <p className='text-fg-muted text-xs'>
          입력 변경으로 인해 갱신이 필요한 산출물이 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div className='flex max-h-[60vh] min-h-0 flex-col gap-3'>
      {/* 결과 배너 */}
      {result && (
        <div className='border-line-primary bg-canvas-surface flex flex-col gap-1 rounded-md border p-3 text-xs'>
          <p className='text-fg-primary font-medium'>재생성 결과</p>
          <ul className='text-fg-muted space-y-0.5'>
            <li className='text-emerald-600 dark:text-emerald-400'>
              ✓ 재생성: {result.regenerated.length}건
            </li>
            {result.skipped.length > 0 && (
              <li>– 건너뜀: {result.skipped.length}건 (수동 편집 필요)</li>
            )}
            {result.failed.length > 0 && (
              <li className='text-red-500'>
                ✗ 실패: {result.failed.length}건
              </li>
            )}
          </ul>
        </div>
      )}

      {/* stale 목록 */}
      {stale.length > 0 && (
        <>
          <div className='flex items-center justify-between text-xs'>
            <label className='text-fg-secondary inline-flex items-center gap-2'>
              <input
                type='checkbox'
                checked={allSelected}
                onChange={toggleAll}
                disabled={autoRegenIds.length === 0}
                className='accent-accent-primary size-3.5'
              />
              자동 재생성 가능 항목 전체 선택 ({autoRegenIds.length})
            </label>
            <span className='text-fg-muted'>총 {stale.length}건 stale</span>
          </div>

          <ScrollArea className='border-line-primary min-h-0 flex-1 rounded-md border'>
            <ul className='divide-line-primary divide-y'>
              {stale.map((item) => (
                <StaleRow
                  key={item.artifact_id}
                  item={item}
                  checked={selected.has(item.artifact_id)}
                  onToggle={() => toggleOne(item.artifact_id)}
                />
              ))}
            </ul>
          </ScrollArea>
        </>
      )}

      {/* 액션 */}
      <div className='flex items-center justify-end gap-2'>
        {onClose && (
          <Button variant='outline' size='sm' onClick={onClose}>
            닫기
          </Button>
        )}
        <Button
          size='sm'
          onClick={handleApply}
          disabled={applying || selected.size === 0}
          className='gap-1.5'
        >
          {applying && <Loader2 className='size-3.5 animate-spin' />}
          {selected.size > 0
            ? `선택 ${selected.size}건 재생성`
            : '재생성할 항목 선택'}
        </Button>
      </div>
    </div>
  );
}

function StaleRow({
  item,
  checked,
  onToggle,
}: {
  item: ImpactedArtifact;
  checked: boolean;
  onToggle: () => void;
}) {
  const Icon = KIND_ICON[item.artifact_type] ?? AlertCircle;
  const canRegenerate = AUTO_REGENERATABLE.has(item.artifact_type);

  return (
    <li
      className={cn(
        'flex items-start gap-3 px-3 py-2 text-xs',
        canRegenerate
          ? 'hover:bg-canvas-primary/40 cursor-pointer'
          : 'opacity-70',
      )}
      onClick={() => canRegenerate && onToggle()}
    >
      <input
        type='checkbox'
        checked={checked}
        onChange={onToggle}
        disabled={!canRegenerate}
        className='accent-accent-primary mt-0.5 size-3.5 shrink-0'
        onClick={(e) => e.stopPropagation()}
      />
      <Icon className='text-fg-muted mt-0.5 size-3.5 shrink-0' />
      <div className='min-w-0 flex-1'>
        <div className='flex items-center gap-2'>
          <span className='text-fg-primary font-mono font-medium'>
            {item.display_id}
          </span>
          {item.current_version_number != null && (
            <span className='text-fg-muted'>v{item.current_version_number}</span>
          )}
          {!canRegenerate && (
            <span className='text-fg-muted text-[10px]'>
              (수동 편집 필요)
            </span>
          )}
        </div>
        <ul className='text-fg-muted mt-0.5 space-y-0.5'>
          {item.stale_reasons.slice(0, 4).map((r, i) => {
            const sourceLabel =
              r.source_display_id ??
              `${r.source_artifact_type.toUpperCase()}-${r.source_artifact_id.slice(0, 6)}`;
            return (
              <li key={i} className='font-mono'>
                {sourceLabel}
                {r.section_id && ` §${r.section_id.slice(0, 6)}`}: v
                {r.referenced_version ?? '?'} → v{r.current_version ?? '?'}
              </li>
            );
          })}
          {item.stale_reasons.length > 4 && (
            <li className='text-fg-muted/60'>
              … +{item.stale_reasons.length - 4}건
            </li>
          )}
        </ul>
      </div>
      {checked && (
        <CheckCircle2 className='size-4 shrink-0 text-emerald-500' />
      )}
      {!canRegenerate && <XCircle className='text-fg-muted/40 size-4 shrink-0' />}
    </li>
  );
}
