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
import { useMemo, useState } from 'react';

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
  const fallbackDesc =
    data.kind === 'clarify'
      ? data.question
      : data.question;

  return (
    <AlertDialog open={open} onOpenChange={(o) => !o && onDismiss()}>
      <AlertDialogContent className='max-w-[480px]'>
        <AlertDialogHeader>
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
        className={cn(hasCandidates ? 'max-w-[720px]' : 'max-w-[480px]')}
      >
        <AlertDialogHeader>
          <AlertDialogTitle
            className={cn(
              'text-fg-primary',
              severity === 'danger' && 'text-destructive',
            )}
          >
            {data.title}
          </AlertDialogTitle>
          <AlertDialogDescription className='whitespace-pre-line'>
            {data.description}
          </AlertDialogDescription>
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
          <div className='border-line-primary bg-canvas-secondary/50 mt-3 rounded-md border'>
            <div className='border-line-primary flex items-center justify-between gap-3 border-b px-3 py-2'>
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
            <div className='max-h-[52vh] overflow-y-auto px-2 py-2'>
              <ul className='space-y-1.5'>
                {candidates.map((candidate, index) => {
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
