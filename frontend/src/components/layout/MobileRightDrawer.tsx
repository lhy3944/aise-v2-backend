'use client';

import { PanelRightOpen } from 'lucide-react';
import { useRef, useState } from 'react';
import { RightPanel } from '@/components/layout/RightPanel';
import { Button } from '@/components/ui/button';
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerTitle,
} from '@/components/ui/drawer';
import { usePanelStore } from '@/stores/panel-store';

export function MobileRightDrawer() {
  const [open, setOpen] = useState(false);
  const sourceViewerData = usePanelStore((s) => s.sourceViewerData);

  const isMobile = usePanelStore((s) => s.isMobile);

  // 출처 버튼 클릭 시 자동 열기/닫기 (모바일에서만 동작)
  const prevSourceDataRef = useRef(sourceViewerData);
  if (isMobile && sourceViewerData !== prevSourceDataRef.current) {
    if (sourceViewerData !== null && !open) {
      setOpen(true);
    } else if (sourceViewerData === null && prevSourceDataRef.current !== null && open) {
      setOpen(false);
    }
    prevSourceDataRef.current = sourceViewerData;
  }

  return (
    <Drawer direction='right' open={open} onOpenChange={setOpen}>
      <Button
        onClick={() => setOpen(true)}
        variant='ghost'
        size='icon'
        className='text-icon-default hover:text-icon-active h-9 w-9 lg:hidden'
      >
        <PanelRightOpen className='h-5 w-5' />
      </Button>

      <DrawerContent
        className='border-line-primary bg-canvas-primary top-15! bottom-0! flex h-auto w-[85vw] flex-col border-l p-0 sm:w-[380px]'
        overlayClassName='top-15!'
      >
        <DrawerTitle className='sr-only'>패널</DrawerTitle>
        <DrawerDescription className='sr-only' />

        <div className='flex-1 overflow-hidden'>
          <RightPanel />
        </div>
      </DrawerContent>
    </Drawer>
  );
}
