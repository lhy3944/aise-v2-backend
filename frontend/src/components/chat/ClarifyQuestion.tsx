'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Forward, HelpCircle } from 'lucide-react';
import { useState } from 'react';

interface ClarifyQuestionProps {
  data: {
    question: string;
    options: string[];
    allow_custom: boolean;
  };
  onAnswer: (answer: string) => void;
}

export function ClarifyQuestion({ data, onAnswer }: ClarifyQuestionProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [customInput, setCustomInput] = useState('');
  const [answered, setAnswered] = useState(false);

  const handleSubmit = () => {
    const answer = selected === '__custom__' ? customInput : selected;
    if (!answer) return;
    setAnswered(true);
    onAnswer(answer);
  };

  if (answered) {
    return (
      <div className='w-full rounded-xl border p-4'>
        <p className='text-fg-muted text-xs'>답변 완료</p>
        <p className='text-fg-primary mt-1 text-sm'>
          {selected === '__custom__' ? customInput : selected}
        </p>
      </div>
    );
  }

  return (
    <div className='w-full rounded-xl border p-4'>
      {/* Question */}
      <div className='mb-3 flex items-start gap-2'>
        <HelpCircle className='text-accent-primary mt-0.5 size-4 shrink-0' />
        <p className='text-fg-primary text-sm font-medium'>{data.question}</p>
      </div>

      {/* Options */}
      {data.options.length > 0 && (
        <div className='mb-3 flex flex-col gap-1.5'>
          {data.options.map((option) => (
            <Button
              key={option}
              onClick={() => setSelected(option)}
              className={cn(
                'rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                selected === option
                  ? 'border-accent-primary text-primary'
                  : 'border-line-primary text-fg-secondary hover:bg-canvas-secondary',
              )}
            >
              {option}
            </Button>
          ))}
        </div>
      )}

      {/* Custom input */}
      {data.allow_custom && (
        <div className='mb-3'>
          <button
            onClick={() => setSelected('__custom__')}
            className={cn(
              'mb-2 w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors',
              selected === '__custom__'
                ? 'border-accent-primary text-accent-primary'
                : 'border-line-primary text-fg-muted hover:bg-canvas-secondary',
            )}
          >
            직접 입력
          </button>
          {selected === '__custom__' && (
            <textarea
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder='답변을 입력하세요...'
              className='bg-canvas-primary border-line-primary text-fg-primary placeholder:text-fg-muted w-full rounded-lg border px-3 py-2 text-sm focus:outline-none'
              rows={2}
              autoFocus
            />
          )}
        </div>
      )}

      {/* Submit */}
      <div className='flex justify-end'>
        <Button
          size='sm'
          onClick={handleSubmit}
          disabled={
            !selected || (selected === '__custom__' && !customInput.trim())
          }
          className='gap-1.5'
        >
          <Forward className='size-3.5' />
          답변하기
        </Button>
      </div>
    </div>
  );
}
