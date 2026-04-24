'use client';

import { cn } from '@/lib/utils';
import type { PlanStep } from '@/types/agent-events';
import {
  AlertCircle,
  Check,
  CircleDashed,
  Loader2,
  Minus,
} from 'lucide-react';

interface PlanProgressProps {
  plan: PlanStep[];
  currentStep?: number;
}

const AGENT_LABELS: Record<string, string> = {
  knowledge_qa: '지식 검색',
  requirement: '요구사항 추출',
  srs_generator: 'SRS 생성',
  testcase_generator: '테스트케이스 생성',
  critic: '검증',
  general_chat: '일반 응답',
};

const STATUS_CONFIG: Record<
  PlanStep['status'],
  { icon: typeof Check; label: string; tone: string }
> = {
  pending: { icon: CircleDashed, label: '대기', tone: 'text-fg-muted' },
  running: { icon: Loader2, label: '실행 중', tone: 'text-amber-600' },
  completed: { icon: Check, label: '완료', tone: 'text-emerald-600' },
  failed: { icon: AlertCircle, label: '실패', tone: 'text-red-500' },
  skipped: { icon: Minus, label: '건너뜀', tone: 'text-fg-muted' },
};

function formatAgent(name: string): string {
  return AGENT_LABELS[name] ?? name;
}

export function PlanProgress({ plan, currentStep }: PlanProgressProps) {
  if (!plan || plan.length === 0) return null;
  return (
    <div className='border-line-primary bg-canvas-surface rounded-md border p-2.5'>
      <div className='text-fg-secondary mb-2 flex items-center gap-1.5 text-[10px] font-semibold tracking-wider uppercase'>
        <span>실행 계획</span>
        <span className='text-fg-muted tabular-nums'>
          ({Math.min(currentStep ?? 0, plan.length - 1) + 1}/{plan.length})
        </span>
      </div>
      <ol className='flex flex-col gap-1'>
        {plan.map((step, idx) => {
          const cfg = STATUS_CONFIG[step.status];
          const Icon = cfg.icon;
          const active = idx === currentStep && step.status === 'running';
          return (
            <li
              key={`${idx}-${step.agent}`}
              className={cn(
                'flex items-center gap-2 rounded px-1.5 py-1 text-xs',
                active && 'bg-amber-500/5',
              )}
            >
              <Icon
                className={cn(
                  'size-3.5 shrink-0',
                  cfg.tone,
                  step.status === 'running' && 'animate-spin',
                )}
              />
              <span className='text-fg-muted w-4 text-[10px] tabular-nums'>
                {idx + 1}
              </span>
              <span
                className={cn(
                  'flex-1 truncate',
                  step.status === 'pending'
                    ? 'text-fg-muted'
                    : 'text-fg-primary',
                )}
              >
                {formatAgent(step.agent)}
              </span>
              <span className={cn('text-[10px]', cfg.tone)}>{cfg.label}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
