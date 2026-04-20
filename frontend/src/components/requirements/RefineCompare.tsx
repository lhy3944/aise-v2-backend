'use client';

import { Check, X, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { RefineResponse } from '@/types/project';

interface RefineCompareProps {
  result: RefineResponse;
  onAccept: (refined: RefineResponse) => void;
  onReject: () => void;
}

export function RefineCompare({ result, onAccept, onReject }: RefineCompareProps) {
  return (
    <div className='border-accent-primary/30 bg-accent-primary/5 rounded-lg border p-4'>
      <div className='mb-3 flex items-center gap-2'>
        <span className='text-accent-primary text-xs font-semibold'>AI 정제 결과</span>
      </div>

      <div className='mb-3 grid grid-cols-[1fr_auto_1fr] items-start gap-3'>
        {/* Original */}
        <div className='border-line-subtle bg-canvas-primary rounded-md border p-3'>
          <span className='text-fg-muted mb-1 block text-xs font-medium'>원문</span>
          <p className='text-fg-secondary text-sm'>{result.original_text}</p>
        </div>

        <ArrowRight className='text-fg-muted mt-6 size-4' />

        {/* Refined */}
        <div className='border-accent-primary/30 bg-canvas-primary rounded-md border p-3'>
          <span className='text-accent-primary mb-1 block text-xs font-medium'>정제문</span>
          <p className='text-fg-primary text-sm'>{result.refined_text}</p>
        </div>
      </div>

      <div className='flex justify-end gap-2'>
        <Button size='sm' variant='ghost' onClick={onReject}>
          <X className='size-3.5' />
          거절
        </Button>
        <Button size='sm' onClick={() => onAccept(result)}>
          <Check className='size-3.5' />
          수락 (정제문으로 추가)
        </Button>
      </div>
    </div>
  );
}
