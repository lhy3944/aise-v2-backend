'use client';

import { LogOut, Settings, User } from 'lucide-react';
import { useState } from 'react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface ProfileDropdownProps {
  onSettingsOpen: () => void;
  onProfileOpen: () => void;
}

export function ProfileDropdown({ onSettingsOpen, onProfileOpen }: ProfileDropdownProps) {
  const [open, setOpen] = useState(false);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button>
          <Avatar className='h-8 w-8'>
            <AvatarFallback className='bg-canvas-surface text-fg-primary text-sm font-medium'>
              A
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className='w-[280px]' align='end' sideOffset={8}>
        <DropdownMenuLabel className='flex items-center gap-3 p-3'>
          <Avatar className='h-10 w-10'>
            <AvatarFallback className='bg-canvas-surface text-fg-primary font-medium'>
              A
            </AvatarFallback>
          </Avatar>
          <div className='flex flex-col'>
            <span className='text-fg-primary text-sm font-medium'>Admin User</span>
            <span className='text-fg-secondary text-xs'>admin@aise.com</span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem className='gap-2 px-3 py-2' onSelect={() => onProfileOpen()}>
          <User className='h-4 w-4' />
          <span>프로필</span>
        </DropdownMenuItem>
        <DropdownMenuItem className='gap-2 px-3 py-2' onSelect={() => onSettingsOpen()}>
          <Settings className='h-4 w-4' />
          <span>앱 설정</span>
        </DropdownMenuItem>
        {/* <DropdownMenuItem className="gap-2 px-3 py-2">
          <LifeBuoy className="h-4 w-4" />
          <span>지원</span>
        </DropdownMenuItem> */}
        <DropdownMenuSeparator />
        <DropdownMenuItem className='text-destructive gap-2 px-3 py-2'>
          <LogOut className='h-4 w-4' />
          <span>로그아웃</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
