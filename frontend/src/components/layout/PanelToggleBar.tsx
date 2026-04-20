'use client';

import { Columns2, PanelLeft, PanelRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { LayoutMode, usePanelStore } from '@/stores/panel-store';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';

const MODES = [
  { mode: LayoutMode.WIDE, icon: PanelLeft, label: '최대' },
  { mode: LayoutMode.SPLIT, icon: Columns2, label: '분할' },
  { mode: LayoutMode.CLOSED, icon: PanelRight, label: '닫기' },
] as const;

export function PanelToggleBar() {
  const layoutMode = usePanelStore((s) => s.layoutMode);
  const setRightPanelPreset = usePanelStore((s) => s.setRightPanelPreset);

  return (
    <div className='hidden items-center lg:flex'>
      {MODES.map(({ mode, icon: Icon, label }) => {
        const isActive = layoutMode === mode;
        return (
          <Tooltip key={mode}>
            <TooltipTrigger asChild>
              <Button
                variant='ghost'
                className={cn(
                  'h-8 w-8 text-fg-muted',
                  isActive &&
                    'bg-fg-primary text-canvas-primary hover:bg-fg-primary/90',
                )}
                onClick={() => setRightPanelPreset(mode)}
              >
                <Icon className='size-4' />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{label}</TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
