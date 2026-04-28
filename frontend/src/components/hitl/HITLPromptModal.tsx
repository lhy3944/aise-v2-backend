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
import { cn } from '@/lib/utils';
import type { HitlData } from '@/types/agent-events';

interface HITLPromptModalProps {
  open: boolean;
  data: HitlData | null;
  /** 사용자가 응답을 확정한 시점에 호출. response 는 백엔드 resume body. */
  onRespond: (response: Record<string, unknown>) => void;
  /** 모달 외부 닫기 (Escape/배경 클릭) — pendingHitl 을 그대로 유지하려면
   *  ChatArea 가 별도 처리해야 한다. 현재는 단순히 cancel 동의로 본다. */
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
    const severity = data.severity ?? 'info';
    const approveLabel = data.actions.approve;
    const rejectLabel = data.actions.reject;

    return (
      <AlertDialog open={open} onOpenChange={(o) => !o && onDismiss()}>
        <AlertDialogContent className='max-w-[480px]'>
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
                  <span className='text-fg-primary font-medium'>
                    {it.label}
                  </span>
                  {' — '}
                  <span>{it.detail}</span>
                </li>
              ))}
            </ul>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={() => onRespond({ action: 'reject' })}
            >
              {rejectLabel}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => onRespond({ action: 'approve' })}
              variant={severity === 'danger' ? 'destructive' : 'default'}
            >
              {approveLabel}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
