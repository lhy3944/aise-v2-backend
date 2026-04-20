'use client';

import { Check, X, Lightbulb } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Suggestion, RequirementType } from '@/types/project';

const TYPE_LABELS: Record<RequirementType, string> = {
  fr: 'FR',
  qa: 'QA',
  constraints: 'Constraints',
  other: 'Other',
};

interface SuggestionPanelProps {
  suggestions: Suggestion[];
  onAccept: (suggestion: Suggestion) => void;
  onReject: (index: number) => void;
  onClose: () => void;
}

export function SuggestionPanel({
  suggestions,
  onAccept,
  onReject,
  onClose,
}: SuggestionPanelProps) {
  if (suggestions.length === 0) return null;

  return (
    <div className='rounded-lg border border-amber-500/30 bg-amber-500/5 p-4'>
      <div className='mb-3 flex items-center justify-between'>
        <div className='flex items-center gap-2'>
          <Lightbulb className='size-4 text-amber-500' />
          <span className='text-fg-primary text-sm font-semibold'>
            AI 보완 제안 ({suggestions.length}건)
          </span>
        </div>
        <Button size='icon-xs' variant='ghost' onClick={onClose}>
          <X className='size-3.5' />
        </Button>
      </div>

      <div className='flex flex-col gap-2'>
        {suggestions.map((suggestion, idx) => (
          <div
            key={idx}
            className='border-line-subtle bg-canvas-primary flex items-start gap-3 rounded-md border p-3'
          >
            <div className='min-w-0 flex-1'>
              <div className='mb-1 flex items-center gap-2'>
                <Badge variant='outline' className='text-xs'>
                  {TYPE_LABELS[suggestion.type]}
                </Badge>
              </div>
              <p className='text-fg-primary text-sm'>{suggestion.text}</p>
              <p className='text-fg-muted mt-1 text-xs'>{suggestion.reason}</p>
            </div>
            <div className='flex shrink-0 gap-1'>
              <Button size='icon-xs' variant='ghost' onClick={() => onReject(idx)} title='거절'>
                <X className='text-fg-muted size-3.5' />
              </Button>
              <Button size='icon-xs' onClick={() => onAccept(suggestion)} title='수락'>
                <Check className='size-3.5' />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
