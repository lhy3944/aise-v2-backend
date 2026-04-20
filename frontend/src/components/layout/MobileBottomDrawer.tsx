'use client';

import { SessionList } from '@/components/chat/SessionList';
import { ProjectSelector } from '@/components/projects/ProjectSelector';
import { Button } from '@/components/ui/button';
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer';
import { SIDEBAR_ACTIONS } from '@/config/navigation';
import { Ellipsis, Plus } from 'lucide-react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { SettingsDialog } from '@/components/overlay/SettingsDialog';
import { usePanelStore } from '@/stores/panel-store';

export function MobileBottomDrawer() {
  const router = useRouter();
  const resetRightPanelView = usePanelStore((s) => s.resetRightPanelView);
  const [open, setOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const actionHandlers: Record<string, () => void> = {
    settings: () => setSettingsOpen(true),
  };

  const BOTTOM_ICONS = SIDEBAR_ACTIONS.map((action) => ({
    ...action,
    onClick: actionHandlers[action.id] ?? (() => {}),
  }));

  const handleNewChat = () => {
    resetRightPanelView();
    router.push('/agent');
    setOpen(false);
  };

  return (
    <div className='flex items-center gap-1 py-1.5'>
      <Button
        onClick={handleNewChat}
        variant='ghost'
        size='icon'
        className='text-icon-default hover:text-icon-active h-9 w-9'
      >
        <Plus className='h-5 w-5' />
      </Button>

      <Drawer open={open} onOpenChange={setOpen}>
        <Button
          onClick={() => setOpen(true)}
          variant='ghost'
          size='icon'
          className='text-icon-default hover:text-icon-active h-9 w-9'
        >
          <Ellipsis className='h-5 w-5' />
        </Button>

        <DrawerContent className='bg-canvas-primary max-h-[85vh]'>
          <DrawerHeader className='border-line-primary flex flex-col gap-3 border-b pb-3'>
            <ProjectSelector />
            <div className='flex items-center justify-between'>
              <DrawerTitle className='text-fg-primary text-base font-semibold'>
              </DrawerTitle>
              <DrawerDescription />
              <Button
                onClick={handleNewChat}
                variant='ghost'
                size='sm'
                className='text-fg-secondary h-8 gap-1.5'
              >
                <Plus className='h-4 w-4' />
                <span className='text-xs'>새 대화</span>
              </Button>
            </div>
          </DrawerHeader>

          <div className='flex h-[50vh] overflow-hidden px-2 py-3'>
            <SessionList onSessionSelect={() => setOpen(false)} />
          </div>

          <div className='border-line-primary flex items-center justify-center gap-6 border-t px-4 py-3'>
            {BOTTOM_ICONS.map(({ icon: Icon, label, onClick }) => (
              <Button
                key={label}
                variant='ghost'
                size='icon'
                className='text-icon-default hover:text-icon-active h-10 w-10'
                onClick={onClick}
              >
                <Icon className='h-5 w-5' />
                <span className='sr-only'>{label}</span>
              </Button>
            ))}
          </div>
        </DrawerContent>
      </Drawer>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  );
}
