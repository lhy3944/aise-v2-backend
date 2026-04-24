'use client';

import { cn } from '@/lib/utils';
import { GitBranch, GitPullRequest, PenSquare } from 'lucide-react';

interface WorkspaceStatusBarProps {
  unstagedCount: number;
  stagedCount: number;
  openPRsCount: number;
  onOpenTray?: () => void;
  activeView?: 'unstaged' | 'staged' | 'prs' | null;
}

/**
 * Unstaged / Staged / Open PRs 3-way 상태 요약 배너.
 * plan §2.2 의 화면 모형 상단 row 를 구현한다.
 */
export function WorkspaceStatusBar({
  unstagedCount,
  stagedCount,
  openPRsCount,
  onOpenTray,
  activeView,
}: WorkspaceStatusBarProps) {
  const total = unstagedCount + stagedCount + openPRsCount;
  if (total === 0) return null;

  return (
    <div className='border-line-primary bg-canvas-surface flex shrink-0 items-center gap-1 border-b px-3 py-1.5'>
      <StatusChip
        icon={PenSquare}
        label='Unstaged'
        count={unstagedCount}
        tone='amber'
        active={activeView === 'unstaged'}
        onClick={onOpenTray}
      />
      <StatusChip
        icon={GitBranch}
        label='Staged'
        count={stagedCount}
        tone='blue'
        active={activeView === 'staged'}
        onClick={onOpenTray}
      />
      <StatusChip
        icon={GitPullRequest}
        label='Open PRs'
        count={openPRsCount}
        tone='violet'
        active={activeView === 'prs'}
        onClick={onOpenTray}
      />
    </div>
  );
}

type Tone = 'amber' | 'blue' | 'violet';

const TONE_CLASSES: Record<Tone, { text: string; bg: string }> = {
  amber: { text: 'text-amber-600', bg: 'bg-amber-500/10' },
  blue: { text: 'text-blue-600', bg: 'bg-blue-500/10' },
  violet: { text: 'text-accent-primary', bg: 'bg-accent-primary/10' },
};

interface StatusChipProps {
  icon: typeof PenSquare;
  label: string;
  count: number;
  tone: Tone;
  active?: boolean;
  onClick?: () => void;
}

function StatusChip({ icon: Icon, label, count, tone, active, onClick }: StatusChipProps) {
  const toneCls = TONE_CLASSES[tone];
  const disabled = count === 0;
  return (
    <button
      type='button'
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] transition-colors',
        disabled
          ? 'text-fg-muted cursor-default opacity-60'
          : active
            ? cn(toneCls.bg, toneCls.text, 'font-medium')
            : 'text-fg-secondary hover:bg-canvas-primary/40',
      )}
    >
      <Icon className='size-3' />
      <span>{label}</span>
      <span
        className={cn(
          'inline-flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] tabular-nums',
          disabled
            ? 'bg-canvas-primary text-fg-muted'
            : cn(toneCls.bg, toneCls.text, 'font-semibold'),
        )}
      >
        {count}
      </span>
    </button>
  );
}
