'use client';

import { cn } from '@/lib/utils';
import { ArrowRight, MessageCircle, Sparkles } from 'lucide-react';

interface SuggestionChipsProps {
  suggestions: string[];
  onSelect: (text: string) => void;
}

export function SuggestionChips({
  suggestions,
  onSelect,
}: SuggestionChipsProps) {
  if (suggestions.length === 0) return null;

  return (
    <div className='mt-3'>
      <div className='text-fg-muted text-xs'>추천 후속 질문</div>
      <div className='divide-line-primary divide-y'>
        {suggestions.map((text, i) => {
          const isCommand = text.trim().startsWith('/');
          const LeadIcon = isCommand ? Sparkles : MessageCircle;
          return (
            <button
              key={i}
              type='button'
              onClick={() => onSelect(text)}
              className={cn(
                'group flex w-full items-center gap-3 px-2 py-3 text-left text-sm',
                'text-fg-secondary hover:text-fg-primary transition-colors',
              )}
            >
              <LeadIcon
                className={cn(
                  'text-fg-muted size-4 shrink-0 transition-colors',
                  'group-hover:text-accent-primary',
                )}
              />
              <span className='flex-1 truncate'>{text}</span>
              <ArrowRight
                className={cn(
                  'text-fg-muted size-4 shrink-0 transition-transform',
                  'group-hover:text-fg-primary group-hover:translate-x-0.5',
                )}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
