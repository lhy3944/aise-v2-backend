'use client';

import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer';
import { ScrollArea } from '@/components/ui/scroll-area';
import { usePanelStore } from '@/stores/panel-store';
import { ArrowRight, Bell } from 'lucide-react';

export function NotificationPanel() {
  const notificationOpen = usePanelStore((s) => s.notificationOpen);

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      usePanelStore.setState({ notificationOpen: false });
    }
  };

  return (
    <Drawer open={notificationOpen} onOpenChange={handleOpenChange} direction='right'>
      <DrawerContent className='w-80 sm:max-w-80'>
        <DrawerDescription />
        <DrawerHeader className='border-muted flex flex-row items-center justify-between border-b px-4 py-5'>
          <div className='flex items-center gap-2'>
            <Bell className='text-fg-primary h-5 w-5' />
            <DrawerTitle className='text-fg-primary text-sm font-semibold'>
              Notifications
            </DrawerTitle>
          </div>
          <DrawerClose className='text-icon-default hover:text-icon-active text-sm transition-colors'>
            <ArrowRight className='h-5 w-5' />
          </DrawerClose>
        </DrawerHeader>
        <ScrollArea className='flex-1'>
          <div className='flex h-full min-h-[200px] items-center justify-center'>
            <span className='text-fg-muted text-sm'>No notifications</span>
          </div>
        </ScrollArea>
      </DrawerContent>
    </Drawer>
  );
}
