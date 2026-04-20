'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { ChevronDown, CheckCircle2, Loader2, AlertCircle, Clock, Wrench } from 'lucide-react';
import { useState } from 'react';

export type ToolCallState =
  | 'pending'
  | 'running'
  | 'completed'
  | 'error';

const STATE_CONFIG: Record<ToolCallState, { icon: typeof Loader2; label: string; color: string }> = {
  pending: { icon: Clock, label: '대기', color: 'text-gray-500 bg-gray-500/10' },
  running: { icon: Loader2, label: '실행 중', color: 'text-amber-600 bg-amber-500/10' },
  completed: { icon: CheckCircle2, label: '완료', color: 'text-green-600 bg-green-500/10' },
  error: { icon: AlertCircle, label: '오류', color: 'text-red-600 bg-red-500/10' },
};

interface ToolCallProps {
  name: string;
  state: ToolCallState;
  input?: Record<string, unknown>;
  output?: string;
  error?: string;
  defaultOpen?: boolean;
}

export function ToolCall({
  name,
  state,
  input,
  output,
  error,
  defaultOpen = false,
}: ToolCallProps) {
  const [open, setOpen] = useState(defaultOpen);
  const config = STATE_CONFIG[state];
  const StatusIcon = config.icon;

  return (
    <div className='border-line-primary my-2 min-w-0 overflow-hidden rounded-lg border'>
      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        className='hover:bg-canvas-surface/50 flex w-full min-w-0 items-center gap-2 px-3 py-2 text-left transition-colors'
      >
        <Wrench className='text-fg-muted size-3.5 shrink-0' />
        <span className='text-fg-primary min-w-0 flex-1 truncate text-xs font-medium'>{name}</span>
        <Badge variant='outline' className={cn('shrink-0 gap-1 text-[10px] [&>svg]:size-3', config.color)}>
          <StatusIcon className={cn(state === 'running' && 'animate-spin')} />
          {config.label}
        </Badge>
        <ChevronDown
          className={cn(
            'text-fg-muted size-3.5 shrink-0 transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>

      {/* Collapsible content */}
      {open && (
        <div className='border-line-primary border-t'>
          {input && Object.keys(input).length > 0 && (
            <div className='border-line-primary border-b px-3 py-2'>
              <p className='text-fg-muted mb-1 text-[10px] font-semibold uppercase'>Input</p>
              <pre className='text-fg-secondary w-full overflow-x-auto text-[11px] leading-relaxed' style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {JSON.stringify(input, null, 2)}
              </pre>
            </div>
          )}
          {output && (
            <div className='px-3 py-2'>
              <p className='text-fg-muted mb-1 text-[10px] font-semibold uppercase'>Output</p>
              <p className='text-fg-secondary text-xs'>{output}</p>
            </div>
          )}
          {error && (
            <div className='px-3 py-2'>
              <p className='mb-1 text-[10px] font-semibold uppercase text-red-500'>Error</p>
              <p className='text-xs text-red-500'>{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
