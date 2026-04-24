'use client';

import { cn } from '@/lib/utils';
import type { DiffFieldEntry } from '@/types/project';
import { Minus, Pencil, Plus } from 'lucide-react';

interface FieldDiffRowProps {
  entry: DiffFieldEntry;
}

interface KindConfig {
  icon: typeof Plus | null;
  label: string;
  bg: string;
  text: string;
  prefix: string;
}

const KIND_CONFIG: Record<DiffFieldEntry['kind'], KindConfig> = {
  added: {
    icon: Plus,
    label: '추가',
    bg: 'border-emerald-500/40 bg-emerald-500/5',
    text: 'text-emerald-600',
    prefix: '+',
  },
  removed: {
    icon: Minus,
    label: '삭제',
    bg: 'border-red-500/40 bg-red-500/5',
    text: 'text-red-500',
    prefix: '-',
  },
  modified: {
    icon: Pencil,
    label: '변경',
    bg: 'border-amber-500/40 bg-amber-500/5',
    text: 'text-amber-600',
    prefix: '~',
  },
  unchanged: {
    icon: null,
    label: '변경 없음',
    bg: 'border-line-primary bg-canvas-primary/30',
    text: 'text-fg-muted',
    prefix: '=',
  },
};

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '(빈 값)';
  if (typeof v === 'string') return v.length > 0 ? v : '(빈 문자열)';
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

export function FieldDiffRow({ entry }: FieldDiffRowProps) {
  const cfg = KIND_CONFIG[entry.kind];
  const Icon = cfg.icon;
  const showBefore = entry.kind === 'removed' || entry.kind === 'modified';
  const showAfter = entry.kind === 'added' || entry.kind === 'modified';
  const showBoth = entry.kind === 'unchanged';

  return (
    <div className={cn('rounded-md border p-2.5', cfg.bg)}>
      <div className='mb-1.5 flex items-center gap-1.5'>
        {Icon && <Icon className={cn('size-3', cfg.text)} />}
        <span className='text-fg-primary font-mono text-xs font-medium'>
          {entry.field_path}
        </span>
        <span className={cn('text-[10px] font-semibold tracking-wide uppercase', cfg.text)}>
          {cfg.label}
        </span>
      </div>

      {showBefore && (
        <DiffValue
          label='이전'
          value={entry.before}
          tone='before'
          prefix={entry.kind === 'removed' ? '-' : '~'}
        />
      )}
      {showAfter && (
        <DiffValue
          label='이후'
          value={entry.after}
          tone='after'
          prefix='+'
        />
      )}
      {showBoth && (
        <DiffValue label='값' value={entry.after ?? entry.before} tone='muted' prefix='=' />
      )}
    </div>
  );
}

interface DiffValueProps {
  label: string;
  value: unknown;
  tone: 'before' | 'after' | 'muted';
  prefix: string;
}

function DiffValue({ label, value, tone, prefix }: DiffValueProps) {
  const toneCls =
    tone === 'before'
      ? 'text-red-600/90'
      : tone === 'after'
        ? 'text-emerald-700'
        : 'text-fg-muted';
  return (
    <div className='mb-0.5 last:mb-0'>
      <span className='text-fg-muted mr-1 text-[10px] uppercase'>{label}</span>
      <pre
        className={cn(
          'bg-canvas-surface border-line-primary/50 rounded border px-2 py-1 font-mono text-[11px] leading-snug whitespace-pre-wrap',
          toneCls,
        )}
      >
        <span className='mr-1 opacity-60'>{prefix}</span>
        {formatValue(value)}
      </pre>
    </div>
  );
}
