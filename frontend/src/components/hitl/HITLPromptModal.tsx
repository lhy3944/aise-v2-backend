'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';
import type { HitlData } from '@/types/agent-events';
import { XIcon } from 'lucide-react';
import { useMemo, useState } from 'react';

const ALL_SECTIONS = '__all__';
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

function HeaderCloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type='button'
      aria-label='닫기'
      className='text-fg-muted hover:text-fg-primary focus-visible:ring-ring absolute top-4 right-4 rounded-xs p-1 opacity-70 transition-opacity hover:opacity-100 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:pointer-events-none'
      onClick={onClick}
    >
      <XIcon className='size-4' />
    </button>
  );
}

interface HITLPromptModalProps {
  open: boolean;
  data: HitlData | null;
  /** 사용자가 응답을 확정한 시점에 호출. response 는 백엔드 resume body. */
  onRespond: (response: Record<string, unknown>) => void;
  /** 모달 외부 닫기 (Escape/배경 클릭) — 응답 없이 pending 상태만 숨긴다. */
  onDismiss: () => void;
}

export function HITLPromptModal({
  open,
  data,
  onRespond,
  onDismiss,
}: HITLPromptModalProps) {
  if (!data) {
    return (
      <AlertDialog open={open} onOpenChange={(o) => !o && onDismiss()}>
        <AlertDialogContent />
      </AlertDialog>
    );
  }

  // ── confirm: title + description + Approve/Reject ────────────────
  if (data.kind === 'confirm') {
    return (
      <ConfirmPrompt
        key={data.interrupt_id}
        open={open}
        data={data}
        onRespond={onRespond}
        onDismiss={onDismiss}
      />
    );
  }

  // ── clarify / decision: PR-3 단계에서는 미지원 안내만 ──────────────
  // PR-4 에서 옵션 select / 다중 선택 UI 도입 예정.
  const fallbackTitle =
    data.kind === 'clarify' ? '추가 정보가 필요합니다' : '선택이 필요합니다';
  const fallbackDesc = data.kind === 'clarify' ? data.question : data.question;

  return (
    <AlertDialog open={open} onOpenChange={(o) => !o && onDismiss()}>
      <AlertDialogContent className='max-w-[480px]'>
        <HeaderCloseButton onClick={onDismiss} />
        <AlertDialogHeader className='pr-8'>
          <AlertDialogTitle className='text-fg-primary'>
            {fallbackTitle}
          </AlertDialogTitle>
          <AlertDialogDescription className='whitespace-pre-line'>
            {fallbackDesc}
            {'\n\n'}
            <span className='text-fg-muted text-xs'>
              (이 형식의 응답 UI 는 다음 단계에서 추가됩니다 — 일단 채팅으로
              답변해주세요.)
            </span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onDismiss}>닫기</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function ConfirmPrompt({
  open,
  data,
  onRespond,
  onDismiss,
}: {
  open: boolean;
  data: Extract<HitlData, { kind: 'confirm' }>;
  onRespond: (response: Record<string, unknown>) => void;
  onDismiss: () => void;
}) {
  const severity = data.severity ?? 'info';
  const candidates = useMemo(
    () => asRecordCandidates(data.context?.records_extracted),
    [data.context],
  );
  const sectionFilters = useMemo(() => {
    const counts = new Map<string, number>();
    for (const candidate of candidates) {
      const label = sectionLabel(candidate);
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
    return Array.from(counts, ([label, count]) => ({ label, count }));
  }, [candidates]);
  const [sectionFilter, setSectionFilter] = useState(ALL_SECTIONS);
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(candidates.map((_, i) => i)),
  );

  const hasCandidates = candidates.length > 0;
  const selectedCount = selected.size;
  const visibleCandidates = useMemo(
    () =>
      candidates
        .map((candidate, index) => ({ candidate, index }))
        .filter(
          ({ candidate }) =>
            sectionFilter === ALL_SECTIONS ||
            sectionLabel(candidate) === sectionFilter,
        ),
    [candidates, sectionFilter],
  );

  const toggle = (index: number, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(index);
      else next.delete(index);
      return next;
    });
  };

  const approve = () => {
    const response: Record<string, unknown> = { action: 'approve' };
    if (hasCandidates) {
      response.selected_indices = [...selected].sort((a, b) => a - b);
    }
    onRespond(response);
  };

  return (
    <AlertDialog open={open} onOpenChange={(o) => !o && onDismiss()}>
      <AlertDialogContent
        className={cn(
          hasCandidates
            ? 'w-[calc(100vw-2rem)] max-w-[920px] data-[size=default]:sm:max-w-[920px]'
            : 'max-w-[480px] data-[size=default]:sm:max-w-[480px]',
        )}
      >
        <HeaderCloseButton onClick={onDismiss} />
        <AlertDialogHeader className='pr-8'>
          <AlertDialogTitle
            className={cn(
              'text-fg-primary',
              severity === 'danger' && 'text-destructive',
            )}
          >
            {data.title}
          </AlertDialogTitle>
          {hasCandidates ? (
            <AlertDialogDescription className='sr-only'>
              {data.description}
            </AlertDialogDescription>
          ) : (
            <AlertDialogDescription className='whitespace-pre-line'>
              {data.description}
            </AlertDialogDescription>
          )}
        </AlertDialogHeader>

        {data.impact && data.impact.length > 0 && (
          <ul className='border-line-primary bg-canvas-secondary mt-2 space-y-1 rounded-md border p-3 text-xs'>
            {data.impact.map((it, i) => (
              <li key={i} className='text-fg-secondary'>
                <span className='text-fg-primary font-medium'>{it.label}</span>
                {' — '}
                <span>{it.detail}</span>
              </li>
            ))}
          </ul>
        )}

        {hasCandidates && (
          <div className='border-line-primary bg-canvas-secondary/50 rounded-md border'>
            <div className='border-line-primary flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2'>
              <div className='flex w-full items-center justify-end gap-3'>
                <span className='text-fg-secondary text-xs'>
                  선택됨 {selectedCount}/{candidates.length}
                </span>
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
              <div className='flex flex-wrap items-center gap-1.5'>
                <button
                  type='button'
                  aria-pressed={sectionFilter === ALL_SECTIONS}
                  className={cn(
                    'border-line-subtle rounded-md border px-2 py-1 text-xs font-medium transition-colors',
                    sectionFilter === ALL_SECTIONS
                      ? 'bg-accent-primary text-accent-foreground border-accent-primary'
                      : 'bg-canvas-primary text-fg-secondary hover:text-fg-primary',
                  )}
                  onClick={() => setSectionFilter(ALL_SECTIONS)}
                >
                  전체 {candidates.length}
                </button>
                {sectionFilters.map((filter) => (
                  <button
                    key={filter.label}
                    type='button'
                    aria-pressed={sectionFilter === filter.label}
                    className={cn(
                      'border-line-subtle rounded-md border px-2 py-1 text-xs font-medium transition-colors',
                      sectionFilter === filter.label
                        ? 'bg-accent-primary text-accent-foreground border-accent-primary'
                        : 'bg-canvas-primary text-fg-secondary hover:text-fg-primary',
                    )}
                    onClick={() => setSectionFilter(filter.label)}
                  >
                    {filter.label} {filter.count}
                  </button>
                ))}
              </div>
            </div>
            <div className='max-h-[52vh] overflow-y-auto px-2 py-2'>
              <ul className='space-y-1.5'>
                {visibleCandidates.map(({ candidate, index }) => {
                  const confidence = formatConfidence(
                    candidate.confidence_score,
                  );
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

        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => onRespond({ action: 'reject' })}>
            {data.actions.reject}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={approve}
            disabled={hasCandidates && selectedCount === 0}
            variant={severity === 'danger' ? 'destructive' : 'default'}
          >
            {data.actions.approve}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
