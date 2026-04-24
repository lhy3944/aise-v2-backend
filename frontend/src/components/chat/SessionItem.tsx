'use client';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useOverlay } from '@/hooks/useOverlay';
import { cn } from '@/lib/utils';
import type { SessionResponse } from '@/services/session-service';
import {
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Share2,
  Trash2,
} from 'lucide-react';
import { useState } from 'react';

interface SessionItemProps {
  session: SessionResponse;
  isActive: boolean;
  onClick: () => void;
  onDelete?: () => void;
  onRename?: (title: string) => void;
}

export function SessionItem({
  session,
  isActive,
  onClick,
  onDelete,
  onRename,
}: SessionItemProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const overlay = useOverlay();

  const handleRename = () => {
    overlay.prompt({
      title: '세션 이름 변경',
      label: '새 이름',
      placeholder: '새 이름을 입력하세요',
      defaultValue: session.title,
      requiredMessage: '이름을 입력하세요',
      maxLength: 100,
      confirmLabel: '변경',
      onConfirm: (value) => {
        if (value !== session.title) onRename?.(value);
      },
    });
  };

  return (
    <div
      className={cn(
        'group relative flex w-full min-w-0 items-center rounded-sm pr-2 transition-colors',
        isActive
          ? 'bg-canvas-surface text-fg-primary'
          : 'text-fg-secondary hover:bg-canvas-surface/50',
      )}
    >
      <button
        onClick={onClick}
        className='flex min-w-0 flex-1 items-center gap-2 px-2.5 py-2 justify-start'
      >
        <MessageSquare className='h-3.5 w-3.5 shrink-0' fill='currentColor' />
        <span className='truncate text-[13px]'>{session.title}</span>
      </button>

      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger asChild>
          <button
            onClick={(e) => e.stopPropagation()}
            className={cn(
              'text-fg-secondary hover:text-fg-primary shrink-0 cursor-pointer rounded p-1 transition-opacity',
              menuOpen ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
            )}
          >
            <MoreHorizontal className='h-4 w-4' />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align='start' side='right' className='w-40'>
          <DropdownMenuItem className='gap-2 text-xs' onClick={handleRename}>
            <Pencil className='h-3.5 w-3.5' />
            이름 변경
          </DropdownMenuItem>
          <DropdownMenuItem className='gap-2 text-xs'>
            <Share2 className='h-3.5 w-3.5' />
            공유
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className='text-destructive focus:text-destructive gap-2 text-xs'
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.();
            }}
          >
            <Trash2 className='h-3.5 w-3.5' />
            삭제
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
