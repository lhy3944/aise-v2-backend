'use client';

import {
  Boxes,
  CheckCircle2,
  CircleSlash,
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
import { useArtifactActionStore } from '@/stores/artifact-action-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { useArtifactStore } from '@/stores/artifact-store';
import type { ArtifactKind } from '@/types/agent-events';
import type {
  ImpactedArtifact,
  ImpactApplyResponse,
  StaleReason,
} from '@/types/project';

const KIND_ICON: Record<string, typeof Database> = {
  record: Database,
  srs: FileText,
  system_model: Boxes,
  data_model: Database,
  design: Layers,
  testcase: FlaskConical,
};

const KIND_LABEL: Record<string, string> = {
  record: '레코드',
  srs: 'SRS',
  system_model: '시스템 모델',
  data_model: '데이터 모델',
  design: '설계(SDD)',
  testcase: '테스트케이스',
};

const AUTO_REGENERATABLE = new Set(['srs', 'system_model', 'data_model', 'design', 'testcase']);

function formatReason(r: StaleReason): string {
  const label =
    r.source_display_id ??
    `${r.source_artifact_type.toUpperCase()}-${r.source_artifact_id.slice(0, 6)}`;

  const section = r.section_id ? ` §${r.section_id.slice(0, 6)}` : '';

  if (r.current_version == null) {
    return `${label}${section}: 삭제됨 (v${r.referenced_version ?? '?'} 참조)`;
  }

  if (r.referenced_version == null) {
    return `${label}${section}: 갱신됨 (현재 v${r.current_version})`;
  }

  return `${label}${section}: v${r.referenced_version} → v${r.current_version}`;
}

interface ImpactPanelProps {
  projectId: string;
  onClose?: () => void;
  onApplyComplete?: () => void;
}

export function ImpactPanel({
  projectId,
  onClose,
  onApplyComplete,
}: ImpactPanelProps) {
  const { stale, loading } = useImpact(projectId);
  const bumpAll = useArtifactRefreshStore((s) => s.bumpAll);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [applying, setApplying] = useState(false);
  const [result, setResult] = useState<ImpactApplyResponse | null>(null);

  const autoRegenIds = useMemo(
    () =>
      stale
        .filter((s) => AUTO_REGENERATABLE.has(s.artifact_type))
        .map((s) => s.artifact_id),
    [stale],
  );

  const allSelected =
    autoRegenIds.length > 0 && autoRegenIds.every((id) => selected.has(id));

  // SRS stale 항목의 artifact_id → 그 SRS를 참조하는 downstream 건수
  const downstreamCounts = useMemo(() => {
    const srsIds = new Set(
      stale.filter((s) => s.artifact_type === 'srs').map((s) => s.artifact_id),
    );
    const counts: Record<string, { design: number; testcase: number }> = {};
    for (const s of srsIds) {
      counts[s] = { design: 0, testcase: 0 };
    }
    for (const item of stale) {
      if (item.artifact_type === 'srs') continue;
      const refersToSrs = item.stale_reasons.some((r) =>
        srsIds.has(r.source_artifact_id),
      );
      if (refersToSrs) {
        for (const r of item.stale_reasons) {
          const c = counts[r.source_artifact_id];
          if (c) {
            if (item.artifact_type === 'design') c.design++;
            else if (item.artifact_type === 'testcase') c.testcase++;
          }
        }
      }
    }
    return counts;
  }, [stale]);

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

    // 갱신 대상 artifact_type → ArtifactKind 매핑
    const kindsToRegen = new Set<ArtifactKind>();
    for (const item of stale) {
      if (selected.has(item.artifact_id)) {
        if (item.artifact_type === 'srs') kindsToRegen.add('srs');
        else if (item.artifact_type === 'design') kindsToRegen.add('design');
        else if (item.artifact_type === 'testcase') kindsToRegen.add('testcase');
      }
    }

    // 스피너 ON + 해당 탭으로 전환
    const setGenerating = useArtifactActionStore.getState().setGenerating;
    const setActiveTab = useArtifactStore.getState().setActiveTab;
    for (const kind of kindsToRegen) {
      setGenerating(kind, true);
    }
    if (kindsToRegen.size > 0) {
      const first = [...kindsToRegen][0];
      const tabMap: Record<string, string> = {
        record: 'records',
        system_model: 'design',
        data_model: 'design',
      };
      setActiveTab((tabMap[first] ?? first) as Parameters<typeof setActiveTab>[0]);
    }

    // 모달 닫기 — 이후 스피너가 탭에 표시됨
    onApplyComplete?.();

    try {
      await impactService.apply(projectId, {
        artifact_ids: Array.from(selected),
      });
      bumpAll();
    } catch {
      // 글로벌 핸들링
    } finally {
      for (const kind of kindsToRegen) {
        setGenerating(kind, false);
      }
      setApplying(false);
      setSelected(new Set());
    }
  };

  if (loading) {
    return (
      <div className='text-fg-muted flex h-32 items-center justify-center gap-2 text-xs'>
        <Loader2 className='size-4 animate-spin' />
        분석 중...
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
    <div className='flex h-[60vh] min-h-0 flex-col gap-3 overflow-hidden'>
      {result && (
        <div className='border-line-primary bg-canvas-surface flex shrink-0 flex-col gap-1 rounded-md border p-3 text-xs'>
          <p className='text-fg-primary font-medium'>갱신 결과</p>
          <ul className='text-fg-muted space-y-0.5'>
            <li className='text-emerald-600 dark:text-emerald-400'>
              ✓ 갱신: {result.regenerated.length}건
            </li>
            {result.skipped.length > 0 && (
              <li>– 건너뜀: {result.skipped.length}건 (수동 편집 필요)</li>
            )}
            {result.failed.length > 0 && (
              <li className='text-red-500'>✗ 실패: {result.failed.length}건</li>
            )}
          </ul>
        </div>
      )}

      {stale.length > 0 && (
        <>
          <div className='flex shrink-0 items-center justify-between text-xs'>
            <label className='text-fg-secondary inline-flex items-center gap-2'>
              <input
                type='checkbox'
                checked={allSelected}
                onChange={toggleAll}
                disabled={autoRegenIds.length === 0}
                className='accent-accent-primary size-4'
              />
              자동 갱신 가능 항목 전체 선택 ({autoRegenIds.length})
            </label>
            <span className='text-fg-muted'>총 {stale.length}건</span>
          </div>

          <ScrollArea className='border-line-primary min-h-0 flex-1 rounded-md border'>
            <ul className='divide-line-primary divide-y'>
              {stale.map((item) => (
                <StaleRow
                  key={item.artifact_id}
                  item={item}
                  checked={selected.has(item.artifact_id)}
                  onToggle={() => toggleOne(item.artifact_id)}
                  downstreamCounts={downstreamCounts}
                />
              ))}
            </ul>
          </ScrollArea>
        </>
      )}

      <div className='flex shrink-0 items-center justify-end gap-2'>
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
          {applying && <Loader2 className='size-4 animate-spin' />}
          {selected.size > 0
            ? `선택 ${selected.size}건 갱신`
            : '갱신할 항목 선택'}
        </Button>
      </div>
    </div>
  );
}

function StaleRow({
  item,
  checked,
  onToggle,
  downstreamCounts,
}: {
  item: ImpactedArtifact;
  checked: boolean;
  onToggle: () => void;
  downstreamCounts: Record<string, { design: number; testcase: number }>;
}) {
  const Icon = KIND_ICON[item.artifact_type] ?? Database;
  const canRegenerate = AUTO_REGENERATABLE.has(item.artifact_type);

  const hasDeleted = item.stale_reasons.some((r) => r.current_version == null);

  const downstream = downstreamCounts[item.artifact_id];
  const hasDownstream =
    downstream && (downstream.design > 0 || downstream.testcase > 0);

  return (
    <li
      className={cn(
        'flex items-start gap-3 px-3 py-2.5 text-xs',
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
        className='accent-accent-primary mt-0.5 size-4 shrink-0'
        onClick={(e) => e.stopPropagation()}
      />
      <Icon className='text-fg-muted mt-0.5 size-4 shrink-0' />
      <div className='min-w-0 flex-1'>
        <div className='flex items-center gap-2'>
          <span className='text-fg-primary font-medium'>{item.display_id}</span>
          {item.current_version_number != null && (
            <span className='text-fg-muted'>
              v{item.current_version_number}
            </span>
          )}
          {hasDeleted && (
            <span className='inline-flex items-center gap-1 rounded border border-red-500/30 bg-red-500/5 px-1.5 py-0.5 text-[10px] font-medium text-red-600 dark:text-red-400'>
              <CircleSlash className='size-3' />
              참조 삭제됨
            </span>
          )}
          {!canRegenerate && (
            <span className='text-fg-muted text-[10px]'>(수동 편집 필요)</span>
          )}
        </div>
        <ul className='text-fg-muted mt-1 space-y-0.5'>
          {item.stale_reasons.slice(0, 4).map((r, i) => (
            <li key={i}>{formatReason(r)}</li>
          ))}
          {item.stale_reasons.length > 4 && (
            <li className='text-fg-muted/60'>
              … +{item.stale_reasons.length - 4}건
            </li>
          )}
        </ul>
        {hasDownstream && (
          <div className='text-fg-muted mt-1.5 text-[10px]'>
            갱신 시 연쇄 영향:{' '}
            {downstream.design > 0 && `설계 ${downstream.design}건`}
            {downstream.design > 0 && downstream.testcase > 0 && ', '}
            {downstream.testcase > 0 && `TC ${downstream.testcase}건`}
          </div>
        )}
      </div>
      {checked && <CheckCircle2 className='size-5 shrink-0 text-emerald-500' />}
      {!canRegenerate && (
        <XCircle className='text-fg-muted/40 size-5 shrink-0' />
      )}
    </li>
  );
}
