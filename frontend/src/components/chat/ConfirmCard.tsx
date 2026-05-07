'use client';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import type { ConfirmData } from '@/types/agent-events';
import type { ArtifactType } from '@/stores/artifact-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { usePanelStore } from '@/stores/panel-store';
import { Check, ExternalLink, Loader2, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react';
import { motion } from 'motion/react';
import { useMemo, useState } from 'react';

const AGENT_TO_TAB: Record<string, ArtifactType> = {
  requirement: 'records',
  srs_generator: 'srs',
  design_generator: 'design',
  testcase_generator: 'testcase',
};

const UNCATEGORIZED_SECTION = '미분류';

interface RecordCandidate {
  content: string;
  section_name?: string | null;
  source_document_name?: string | null;
  source_location?: string | null;
  confidence_score?: number | null;
}

function asRecordCandidates(value: unknown): RecordCandidate[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item): RecordCandidate | null => {
      if (!item || typeof item !== 'object') return null;
      const record = item as Record<string, unknown>;
      const content = record.content;
      if (typeof content !== 'string' || !content.trim()) return null;
      return {
        content,
        section_name:
          typeof record.section_name === 'string' ? record.section_name : null,
        source_document_name:
          typeof record.source_document_name === 'string'
            ? record.source_document_name
            : null,
        source_location:
          typeof record.source_location === 'string'
            ? record.source_location
            : null,
        confidence_score:
          typeof record.confidence_score === 'number'
            ? record.confidence_score
            : null,
      };
    })
    .filter((item): item is RecordCandidate => item !== null);
}

function formatConfidence(value?: number | null): string | null {
  if (typeof value !== 'number') return null;
  return `${Math.round(value * 100)}%`;
}

function sectionLabel(candidate: RecordCandidate): string {
  return candidate.section_name?.trim() || UNCATEGORIZED_SECTION;
}

function SeverityIcon({ severity }: { severity: ConfirmData['severity'] }) {
  switch (severity) {
    case 'danger':
      return <ShieldAlert className='size-4 text-destructive' />;
    case 'warning':
      return <ShieldQuestion className='size-4 text-fg-muted' />;
    default:
      return <ShieldCheck className='size-4 text-accent-primary' />;
  }
}

interface ConfirmCardProps {
  data: ConfirmData;
  onRespond: (response: Record<string, unknown>) => void;
  responded?: boolean;
  approved?: boolean | null;
  /** 산출물 생성 진행 중 여부 — 승인 후 resume 스트리밍 중이면 true */
  artifactPending?: boolean;
}

export function ConfirmCard({
  data,
  onRespond,
  responded,
  approved,
  artifactPending,
}: ConfirmCardProps) {
  const severity = data.severity ?? 'info';
  const candidates = useMemo(
    () => asRecordCandidates(data.context?.records_extracted),
    [data.context],
  );
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(candidates.map((_, i) => i)),
  );

  const hasCandidates = candidates.length > 0;
  const selectedCount = selected.size;

  const toggle = (index: number, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(index);
      else next.delete(index);
      return next;
    });
  };

  const handleApprove = () => {
    const response: Record<string, unknown> = { action: 'approve' };
    if (hasCandidates) {
      response.selected_indices = [...selected].sort((a, b) => a - b);
    }
    onRespond(response);
  };

  const handleReject = () => {
    onRespond({ action: 'reject' });
  };

  const artifactKind = data.context?.artifact_kind as string | undefined;
  const targetTab = artifactKind ? AGENT_TO_TAB[artifactKind] : undefined;

  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const rightPanelOpen = usePanelStore((s) => s.rightPanelOpen);
  const toggleRightPanel = usePanelStore((s) => s.toggleRightPanel);

  const navigateToArtifact = () => {
    if (!targetTab) return;
    setActiveTab(targetTab);
    if (!rightPanelOpen) toggleRightPanel();
  };

  if (responded) {
    return (
      <div
        data-hitl-interrupt-id={data.interrupt_id}
        className='border-line-primary bg-canvas-surface w-full rounded-xl border'
      >
        <div className='flex items-center gap-2 px-4 py-3'>
          <SeverityIcon severity={severity} />
          <span className='text-fg-primary text-sm font-medium'>
            {data.title}
          </span>
        </div>
        <div className='border-line-primary flex items-center justify-between border-t px-4 py-2.5'>
          <span
            className={cn(
              'text-xs font-medium',
              approved ? 'text-accent-primary' : 'text-fg-muted',
            )}
          >
            {approved ? '승인됨' : '거부됨'}
          </span>
          {approved && targetTab && (
            artifactPending ? (
              <span className='text-fg-muted flex items-center gap-1 text-xs font-medium'>
                <Loader2 className='size-3 animate-spin' />
                생성 중...
              </span>
            ) : (
              <button
                type='button'
                onClick={navigateToArtifact}
                className='text-accent-primary hover:text-accent-primary/80 flex items-center gap-1 text-xs font-medium transition-colors'
              >
                산출물 보기
                <ExternalLink className='size-3' />
              </button>
            )
          )}
        </div>
      </div>
    );
  }

  return (
    <motion.div
      data-hitl-interrupt-id={data.interrupt_id}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.4 }}
      className='border-line-primary bg-canvas-surface w-full overflow-hidden rounded-xl border'
    >
      {/* Header */}
      <div className='flex items-start gap-2 px-4 py-3'>
        <SeverityIcon severity={severity} />
        <div className='min-w-0 flex-1'>
          <p
            className={cn(
              'text-sm font-medium',
              severity === 'danger' ? 'text-destructive' : 'text-fg-primary',
            )}
          >
            {data.title}
          </p>
          {data.description && (
            <p className='text-fg-secondary mt-1 whitespace-pre-line text-xs'>
              {data.description}
            </p>
          )}
        </div>
      </div>

      {/* Impact */}
      {data.impact && data.impact.length > 0 && (
        <div className='border-line-primary border-t px-4 py-2'>
          <ul className='space-y-1'>
            {data.impact.map((it, i) => (
              <li key={i} className='text-fg-secondary text-xs'>
                <span className='text-fg-primary font-medium'>{it.label}</span>
                {' — '}
                <span>{it.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Record candidates */}
      {hasCandidates && (
        <div className='border-line-primary border-t'>
          <div className='flex items-center justify-between gap-2 px-4 py-2'>
            <span className='text-fg-secondary text-xs'>
              선택됨 {selectedCount}/{candidates.length}
            </span>
            <div className='flex items-center gap-2'>
              <button
                type='button'
                className='text-accent-primary text-xs font-medium'
                onClick={() =>
                  setSelected(new Set(candidates.map((_, i) => i)))
                }
              >
                전체 선택
              </button>
              <button
                type='button'
                className='text-fg-muted hover:text-fg-secondary text-xs font-medium'
                onClick={() => setSelected(new Set())}
              >
                선택 해제
              </button>
            </div>
          </div>
          <div className='max-h-[40vh] overflow-y-auto px-4 pb-2'>
            <ul className='space-y-1.5'>
              {candidates.map((candidate, index) => {
                const confidence = formatConfidence(candidate.confidence_score);
                return (
                  <li
                    key={`${index}-${candidate.content.slice(0, 24)}`}
                    className='border-line-subtle bg-canvas-primary flex items-start gap-2 rounded-md border px-2.5 py-2'
                  >
                    <Checkbox
                      className='mt-0.5'
                      checked={selected.has(index)}
                      onCheckedChange={(checked) => toggle(index, checked)}
                      aria-label={`${index + 1}번 후보 선택`}
                    />
                    <div className='min-w-0 flex-1'>
                      <p className='text-fg-primary text-xs leading-5'>
                        {candidate.content}
                      </p>
                      <div className='text-fg-muted mt-1 flex flex-wrap gap-x-2 gap-y-1 text-[11px]'>
                        {candidate.section_name && (
                          <span>{candidate.section_name}</span>
                        )}
                        {candidate.source_document_name && (
                          <span>{candidate.source_document_name}</span>
                        )}
                        {candidate.source_location && (
                          <span>{candidate.source_location}</span>
                        )}
                        {confidence && <span>신뢰도 {confidence}</span>}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className='border-line-primary flex justify-end gap-2 border-t px-4 py-2.5'>
        <Button variant='outline' size='sm' onClick={handleReject}>
          {data.actions.reject}
        </Button>
        <Button
          size='sm'
          onClick={handleApprove}
          disabled={hasCandidates && selectedCount === 0}
          variant={severity === 'danger' ? 'destructive' : 'default'}
        >
          {data.actions.approve}
        </Button>
      </div>
    </motion.div>
  );
}
