'use client';

import { CheckIcon } from 'lucide-react';
import * as React from 'react';
import { cn } from '@/lib/utils';

interface CheckboxProps extends Omit<React.ComponentProps<'button'>, 'onChange'> {
  checked?: boolean;
  indeterminate?: boolean;
  onCheckedChange?: (checked: boolean) => void;
}

function Checkbox({
  className,
  checked = false,
  indeterminate = false,
  onCheckedChange,
  ...props
}: CheckboxProps) {
  return (
    <button
      type='button'
      role='checkbox'
      aria-checked={indeterminate ? 'mixed' : checked}
      data-state={checked ? 'checked' : 'unchecked'}
      className={cn(
        'peer border-input inline-flex size-4 shrink-0 items-center justify-center rounded-sm border shadow-xs transition-colors',
        'focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-1 focus-visible:outline-none',
        'disabled:cursor-not-allowed disabled:opacity-50',
        (checked || indeterminate) && 'border-primary bg-primary text-primary-foreground',
        className,
      )}
      onClick={() => onCheckedChange?.(!checked)}
      {...props}
    >
      {indeterminate ? (
        <span className='size-2 rounded-[1px] bg-current' />
      ) : checked ? (
        <CheckIcon className='size-3' />
      ) : null}
    </button>
  );
}

export { Checkbox };
