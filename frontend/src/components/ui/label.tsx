'use client';

import { cva, type VariantProps } from 'class-variance-authority';
import { Label as LabelPrimitive } from 'radix-ui';
import * as React from 'react';
import { cn } from '@/lib/utils';

const labelVariants = cva(
  'flex items-center gap-2 leading-none select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'text-sm font-medium',
        field: 'text-fg-muted text-xs',
        caption: 'text-fg-muted text-[11px] font-semibold uppercase tracking-wider',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

function Label({
  className,
  variant,
  ...props
}: React.ComponentProps<typeof LabelPrimitive.Root> & VariantProps<typeof labelVariants>) {
  return (
    <LabelPrimitive.Root
      data-slot='label'
      className={cn(labelVariants({ variant }), className)}
      {...props}
    />
  );
}

export { Label, labelVariants };
