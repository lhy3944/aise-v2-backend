'use client';

import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from '@/components/ui/drawer';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { cn } from '@/lib/utils';
import { usePanelStore } from '@/stores/panel-store';
import { useReadinessStore } from '@/stores/readiness-store';
import { BookOpen, CheckCircle2, FolderOpen, LayoutList, X, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '../ui/button';

interface ProjectReadinessCardProps {
  projectId: string;
  onNavigate?: (tab: string) => void;
}

const ITEMS = [
  { key: 'knowledge' as const, icon: FolderOpen, tab: 'knowledge' },
  { key: 'glossary' as const, icon: BookOpen, tab: 'glossary' },
  { key: 'sections' as const, icon: LayoutList, tab: 'sections' },
];

function ReadinessDetails({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const data = useReadinessStore((s) => s.data);
  if (!data) return null;

  return (
    <div className='flex flex-col gap-1.5'>
      {ITEMS.map(({ key, icon: Icon, tab }) => {
        const item = data[key];
        return (
          <button
            key={key}
            onClick={() => onNavigate?.(tab)}
            className='hover:bg-canvas-surface flex items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors'
          >
            {item.sufficient ? (
              <CheckCircle2 className='size-4 shrink-0 text-green-500' />
            ) : (
              <XCircle className='size-4 shrink-0 text-amber-500' />
            )}
            <span className='text-fg-secondary flex-1 text-sm'>{item.label}</span>
            <Icon className='text-fg-muted size-4 shrink-0' />
            <span
              className={cn(
                'text-sm font-semibold',
                item.sufficient ? 'text-green-600' : 'text-amber-600',
              )}
            >
              {item.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function ProjectReadinessCard({ projectId, onNavigate }: ProjectReadinessCardProps) {
  const data = useReadinessStore((s) => s.data);
  const fetch = useReadinessStore((s) => s.fetch);
  const isMobile = usePanelStore((s) => s.isMobile);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    fetch(projectId);
  }, [fetch, projectId]);

  if (!data) return null;

  const dotClass = cn('size-2.5 rounded-full', data.is_ready ? 'bg-green-500' : 'bg-amber-500');

  const triggerButton = (
    <Button
      variant={'outline'}
      size={'xs'}
      className={cn(
        'flex items-center gap-1.5 rounded-full px-2 py-1 transition-colors md:px-3 md:py-1.5',
        data.is_ready ? 'dark:text-green-400' : 'dark:text-amber-400',
      )}
    >
      <span className={dotClass} />
      {data.is_ready ? '설정 완료' : '설정 필요'}
    </Button>
  );

  // 모바일: Drawer (바텀시트)
  if (isMobile) {
    return (
      <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
        <DrawerTrigger asChild>{triggerButton}</DrawerTrigger>
        <DrawerContent>
          <DrawerHeader className='flex items-center justify-between'>
            <DrawerTitle className='text-sm'>Agent 실행 준비도</DrawerTitle>
            <DrawerClose className='text-fg-muted'>
              <X className='size-4' />
            </DrawerClose>
          </DrawerHeader>
          <div className='px-4 pb-6'>
            <ReadinessDetails
              onNavigate={(tab) => {
                setDrawerOpen(false);
                onNavigate?.(tab);
              }}
            />
          </div>
        </DrawerContent>
      </Drawer>
    );
  }

  // 데스크탑: HoverCard (팝오버)
  return (
    <HoverCard openDelay={200} closeDelay={100}>
      <HoverCardTrigger asChild>{triggerButton}</HoverCardTrigger>
      <HoverCardContent align='end' className='w-56 p-3'>
        <p className='text-fg-primary mb-2 text-xs font-semibold'>Agent 실행 준비도</p>
        <ReadinessDetails onNavigate={onNavigate} />
      </HoverCardContent>
    </HoverCard>
  );
}
