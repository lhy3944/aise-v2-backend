'use client';

import { useState } from 'react';
import { Check, ListChecks } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ExtractedRequirementsProps {
  requirements: { type: string; text: string; reason: string }[];
  onAccept: (requirements: { type: string; text: string }[]) => void;
}

const TYPE_LABELS: Record<string, string> = {
  fr: 'FR',
  qa: 'QA',
  constraints: 'CON',
};

export function ExtractedRequirements({ requirements, onAccept }: ExtractedRequirementsProps) {
  const [selected, setSelected] = useState<Set<number>>(new Set(requirements.map((_, i) => i)));
  const [accepted, setAccepted] = useState(false);

  const toggleItem = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const handleAccept = () => {
    const chosen = requirements
      .filter((_, i) => selected.has(i))
      .map((r) => ({ type: r.type, text: r.text }));
    setAccepted(true);
    onAccept(chosen);
  };

  if (accepted) {
    return (
      <div className='bg-canvas-surface border-line-primary rounded-xl border p-4'>
        <div className='text-fg-muted flex items-center gap-1.5 text-xs'>
          <Check className='size-3.5' />
          {selected.size}개 요구사항 반영 완료
        </div>
      </div>
    );
  }

  return (
    <div className='bg-canvas-surface border-line-primary w-full rounded-xl border p-4'>
      <div className='mb-3 flex items-center gap-2'>
        <ListChecks className='text-fg-secondary size-4' />
        <span className='text-fg-primary text-sm font-medium'>추출된 요구사항</span>
        <Badge variant='secondary' className='text-xs'>
          {requirements.length}개
        </Badge>
      </div>

      <div className='mb-3 flex flex-col gap-1.5'>
        {requirements.map((req, i) => (
          <button
            key={i}
            onClick={() => toggleItem(i)}
            className={cn(
              'flex items-start gap-2 rounded-lg border px-3 py-2 text-left transition-colors',
              selected.has(i)
                ? 'border-accent-primary'
                : 'border-line-primary opacity-50',
            )}
          >
            <div
              className={cn(
                'mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border',
                selected.has(i)
                  ? 'border-accent-primary bg-accent-primary text-white'
                  : 'border-line-primary',
              )}
            >
              {selected.has(i) && <Check className='size-3' />}
            </div>
            <div className='flex-1'>
              <div className='flex items-center gap-1.5'>
                <Badge variant='outline' className='text-[10px]'>
                  {TYPE_LABELS[req.type] ?? req.type.toUpperCase()}
                </Badge>
                <span className='text-fg-primary text-sm'>{req.text}</span>
              </div>
              {req.reason && (
                <p className='text-fg-muted mt-0.5 text-xs'>{req.reason}</p>
              )}
            </div>
          </button>
        ))}
      </div>

      <div className='flex justify-end'>
        <Button size='sm' onClick={handleAccept} disabled={selected.size === 0} className='gap-1.5'>
          <Check className='size-3.5' />
          선택 항목 반영 ({selected.size}개)
        </Button>
      </div>
    </div>
  );
}
