'use client';

import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  CalendarClock,
  Database,
  Link,
  Palette,
  Settings,
  Sparkles,
  User,
  X,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { SettingsAccount } from '@/components/overlay/SettingsAccount';
import { SettingsGeneral } from '@/components/overlay/SettingsGeneral';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { Tabs, TabsList, TabsTrigger } from '../ui/tabs';

interface SettingsMenuItem {
  id: string;
  label: string;
  icon: LucideIcon;
  content: ReactNode;
}

const SETTINGS_MENU: SettingsMenuItem[] = [
  {
    id: 'account',
    label: '계정',
    icon: User,
    content: <SettingsAccount />,
  },
  {
    id: 'general',
    label: '설정',
    icon: Settings,
    content: <SettingsGeneral />,
  },
  {
    id: 'usage',
    label: '사용량',
    icon: BarChart3,
    content: <p className='text-fg-muted text-sm'>사용량</p>,
  },
  {
    id: 'schedule',
    label: '예약 작업',
    icon: CalendarClock,
    content: <p className='text-fg-muted text-sm'>예약 작업</p>,
  },
  {
    id: 'data',
    label: '데이터 제어',
    icon: Database,
    content: <p className='text-fg-muted text-sm'>데이터 제어</p>,
  },
  {
    id: 'personalize',
    label: '개인화',
    icon: Palette,
    content: <p className='text-fg-muted text-sm'>개인화</p>,
  },
  {
    id: 'skills',
    label: '스킬',
    icon: Sparkles,
    content: <p className='text-fg-muted text-sm'>스킬</p>,
  },
  {
    id: 'integration',
    label: '통합',
    icon: Link,
    content: <p className='text-fg-muted text-sm'>통합</p>,
  },
];

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialTab?: string;
}

export function SettingsDialog({ open, onOpenChange, initialTab }: SettingsDialogProps) {
  const [activeId, setActiveId] = useState(() => initialTab ?? 'general');

  // props 변경에 따른 state 동기화 — React 공식 "렌더 중 setState" 패턴
  const [prevOpen, setPrevOpen] = useState(open);
  const [prevInitialTab, setPrevInitialTab] = useState(initialTab);
  if (prevOpen !== open || prevInitialTab !== initialTab) {
    setPrevOpen(open);
    setPrevInitialTab(initialTab);
    if (open) {
      setActiveId(initialTab ?? 'general');
    }
  }

  const activeItem = SETTINGS_MENU.find((item) => item.id === activeId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className={cn(
          'flex flex-col gap-0 overflow-hidden p-0',
          'max-md:h-[70dvh] max-md:max-w-[calc(100%-8px)]',
          'md:h-[560px] md:max-w-[720px] md:flex-row',
        )}
      >
        {/* ── 데스크탑: 좌측 사이드바 ── */}
        <nav className='border-line-primary bg-canvas-secondary/50 hidden w-[200px] shrink-0 flex-col border-r py-4 md:flex'>
          <DialogTitle className='text-fg-primary px-5 pb-4 text-lg font-semibold'>
            앱 설정
            <Button
              variant='ghost'
              size='icon'
              onClick={() => onOpenChange(false)}
              className='text-icon-default hover:text-icon-active absolute top-4 right-4'
            >
              <X className='h-5 w-5' />
            </Button>
          </DialogTitle>
          <ScrollArea className='flex-1'>
            <div className='flex flex-col gap-0.5 px-2'>
              {SETTINGS_MENU.map(({ id, label, icon: Icon }) => (
                <Button
                  key={id}
                  variant='ghost'
                  onClick={() => setActiveId(id)}
                  className={cn(
                    'h-9 justify-start gap-2.5 px-3 text-sm font-normal',
                    activeId === id
                      ? 'bg-canvas-surface text-fg-primary'
                      : 'text-fg-secondary hover:text-fg-primary',
                  )}
                >
                  <Icon className='size-4 shrink-0' />
                  {label}
                </Button>
              ))}
            </div>
          </ScrollArea>
        </nav>

        {/* ── 모바일: 상단 헤더 + 탭 네비게이션 ── */}
        <div className='border-line-primary flex flex-col border-b md:hidden'>
          <div className='flex items-center justify-between px-4 pt-4 pb-2'>
            <DialogTitle className='text-fg-primary text-lg font-semibold'>
              앱 설정
              <Button
                variant='ghost'
                size='icon'
                onClick={() => onOpenChange(false)}
                className='text-icon-default hover:text-icon-active absolute top-4 right-4'
              >
                <X className='h-5 w-5' />
              </Button>
            </DialogTitle>
          </div>
          <div className='relative'>
            <ScrollArea className='w-full'>
              <div className='flex items-center gap-1 px-4 pr-8 pb-[10px]'>
                <Tabs value={activeId} onValueChange={setActiveId}>
                  <TabsList variant={'line'}>
                    {SETTINGS_MENU.map(({ id, label }) => (
                      <TabsTrigger key={id} value={id}>
                        {label}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
              </div>
              <ScrollBar orientation='horizontal' />
            </ScrollArea>
            <div className='from-background pointer-events-none absolute top-0 bottom-2.5 left-0 w-4 bg-linear-to-r to-transparent' />
            <div className='from-background pointer-events-none absolute top-0 right-0 bottom-2.5 w-8 bg-linear-to-l to-transparent' />
          </div>
        </div>

        {/* ── 컨텐츠 영역 ── */}
        <div className='flex flex-1 flex-col overflow-hidden'>
          {/* 데스크탑에서만 컨텐츠 상단에 제목 표시 */}
          <div className='border-line-primary hidden border-b px-6 pt-6 pb-4 md:block'>
            <h2 className='text-fg-primary text-lg font-semibold'>{activeItem?.label}</h2>
          </div>
          <ScrollArea className='flex flex-1 flex-col items-start gap-[32px] -stretch overflow-y-auto px-4 py-4'>
            {activeItem?.content}
          </ScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  );
}
