'use client';

import { ScrollArea as ScrollAreaPrimitive } from 'radix-ui';
import * as React from 'react';
import { cn } from '@/lib/utils';

function ScrollArea({
  className,
  children,
  viewportRef,
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.Root> & {
  viewportRef?: React.Ref<HTMLDivElement>;
}) {
  return (
    <ScrollAreaPrimitive.Root
      data-slot='scroll-area'
      className={cn('group/scroll relative', className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        ref={viewportRef}
        data-slot='scroll-area-viewport'
        // Radix Viewport 는 내부에 `display: table` wrapper 를 자동 생성해
        // 콘텐츠가 부모보다 클 경우 viewport 폭을 늘려 horizontal overflow 를
        // 만든다. wrapper 를 block + 100% 폭 + min-w-0 으로 강제해 콘텐츠가
        // 부모 가로폭에 항상 맞춰지도록 한다.
        className='focus-visible:ring-ring/50 size-full rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-1 focus-visible:outline-1 [&>div]:block! [&>div]:w-full! [&>div]:min-w-0!'
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollBar />
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  );
}

function ScrollBar({
  className,
  orientation = 'vertical',
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>) {
  return (
    <ScrollAreaPrimitive.ScrollAreaScrollbar
      data-slot='scroll-area-scrollbar'
      orientation={orientation}
      className={cn(
        'flex touch-none p-px opacity-0 transition-opacity duration-300 select-none group-hover/scroll:opacity-100',
        orientation === 'vertical' && 'h-full w-2 border-l border-l-transparent',
        orientation === 'horizontal' && 'h-1.5 flex-col border-t border-t-transparent',
        className,
      )}
      {...props}
    >
      <ScrollAreaPrimitive.ScrollAreaThumb
        data-slot='scroll-area-thumb'
        className='bg-fg-muted hover:bg-fg-secondary relative flex-1 rounded-full transition-colors'
      />
    </ScrollAreaPrimitive.ScrollAreaScrollbar>
  );
}

export { ScrollArea, ScrollBar };
