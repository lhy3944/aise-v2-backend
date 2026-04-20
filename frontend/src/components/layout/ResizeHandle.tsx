'use client';

import { GripVertical } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '../ui/button';

interface ResizeHandleProps {
  isOpen?: boolean;
  isResizing?: boolean;
  onPointerDown: (e: React.MouseEvent | React.TouchEvent) => void;
}

export function ResizeHandle({
  isOpen = false,
  isResizing = false,
  onPointerDown,
}: ResizeHandleProps) {
  if (!isOpen) {
    // 닫힌 상태: 그립 버튼만 드래그/클릭 가능
    return (
      <div className='absolute top-0 left-0 z-10 flex h-full items-center'>
        <div
          className={cn(
            'absolute top-1/2 -translate-y-1/2 transition-[right] duration-150',
            isResizing ? 'right-0' : 'right-2',
          )}
        >
          <Button
            variant='ghost'
            size='icon-sm'
            className='bg-border/30 w-6 cursor-col-resize border-0 shadow-none ring-0'
            onMouseDown={onPointerDown}
            onTouchStart={onPointerDown}
          >
            <GripVertical />
          </Button>
        </div>
      </div>
    );
  }

  // 열린 상태: 히트 영역을 오른쪽(패널 안쪽)에 배치
  return (
    <div
      onMouseDown={onPointerDown}
      onTouchStart={onPointerDown}
      className={cn(
        'absolute top-0 left-0 z-10 h-full w-3 cursor-col-resize select-none',
        'group flex items-center justify-center',
        'hover:bg-border/30 transition-all duration-150 hover:w-4',
      )}
    >
      {/* 가이드 선 */}
      <div className='bg-line-primary group-hover:bg-accent-primary absolute left-0 h-full w-px transition-colors duration-150' />

      {/* hover 시 그립 인디케이터 */}
      <div className='absolute top-1/2 -translate-y-1/2 opacity-0 transition-opacity duration-150 group-hover:opacity-100'>
        <Button variant='ghost' size='icon-sm' className='w-3'>
          <GripVertical />
        </Button>
      </div>
    </div>
  );
}
