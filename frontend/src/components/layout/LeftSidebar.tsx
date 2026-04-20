'use client';

import { PanelLeftClose, PanelLeftOpen, Plus } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ProjectSelector } from '@/components/projects/ProjectSelector';
import { SessionList } from '@/components/chat/SessionList';
import { SettingsDialog } from '@/components/overlay/SettingsDialog';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { SIDEBAR_ACTIONS } from '@/config/navigation';
import { ReadinessMiniView } from '@/components/layout/ReadinessMiniView';
import { usePanelStore } from '@/stores/panel-store';


export function LeftSidebar() {
  const router = useRouter();
  const leftSidebarOpen = usePanelStore((s) => s.leftSidebarOpen);
  const toggleLeftSidebar = usePanelStore((s) => s.toggleLeftSidebar);
  const resetRightPanelView = usePanelStore((s) => s.resetRightPanelView);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleNewChat = () => {
    resetRightPanelView();
    router.push('/agent');
  };

  const actionHandlers: Record<string, () => void> = {
    settings: () => setSettingsOpen(true),
    project: () => router.push('/projects'),
  };

  const BOTTOM_ICONS = SIDEBAR_ACTIONS.map((action) => ({
    ...action,
    onClick: actionHandlers[action.id] ?? (() => {}),
  }));

  return (
    <>
      <AnimatePresence mode='popLayout'>
        {leftSidebarOpen ? (
          <motion.div
            key='expanded'
            initial={{ width: 0, opacity: 0 }}
            animate={{
              width: 220,
              opacity: 1,
              transition: { type: 'spring', stiffness: 400, damping: 30 },
            }}
            exit={{
              width: 0,
              opacity: 0,
              transition: { duration: 0.2, ease: 'easeOut' },
            }}
            className='h-full shrink-0 overflow-hidden'
          >
            <div className='flex h-full w-[220px] flex-col gap-2 py-1.5 pl-3'>
              <div className='flex items-center justify-between'>
                <Button
                  onClick={handleNewChat}
                  className='text-fg-primary flex items-center gap-1.5'
                  variant='ghost'
                >
                  <Plus className='h-5 w-5' />
                  <span className='text-[13px] font-medium'>새 대화</span>
                </Button>
                <Button
                  onClick={toggleLeftSidebar}
                  variant='ghost'
                  size='icon'
                  className='text-icon-default hover:text-icon-active'
                >
                  <PanelLeftClose className='h-5 w-5' />
                </Button>
              </div>

              {/* Project Selector */}
              <div className='pr-3'>
                <ProjectSelector />
              </div>

              {/* Readiness Mini View */}
              <div className='pr-3'>
                <ReadinessMiniView />
              </div>

              <SessionList />

              <div className='border-line-primary mt-auto flex items-center justify-center gap-4 border-t pt-3'>
                {BOTTOM_ICONS.map(({ icon: Icon, label, onClick }) => (
                  <Tooltip key={label}>
                    <TooltipTrigger asChild>
                      <Button
                        variant='ghost'
                        size='icon'
                        className='text-icon-default hover:text-icon-active'
                        onClick={onClick}
                      >
                        <Icon className='h-5 w-5' />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side='top'>{label}</TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key='collapsed'
            initial={{ width: 0, opacity: 0 }}
            animate={{
              width: 60,
              opacity: 1,
              transition: { type: 'spring', stiffness: 400, damping: 30 },
            }}
            exit={{
              width: 0,
              opacity: 0,
              transition: { duration: 0.2, ease: 'easeOut' },
            }}
            className='h-full shrink-0 overflow-hidden'
          >
            <div className='flex h-full w-[60px] flex-col items-center justify-between border-r py-4'>
              <div className='flex flex-col items-center gap-2'>
                <Button
                  onClick={toggleLeftSidebar}
                  variant='ghost'
                  size='icon'
                  className='text-icon-default hover:text-icon-active h-9 w-9'
                >
                  <PanelLeftOpen className='h-5 w-5' />
                </Button>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={handleNewChat}
                      variant='ghost'
                      size='icon'
                      className='text-icon-default hover:text-icon-active h-9 w-9'
                    >
                      <Plus className='h-5 w-5' />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side='right'>새 대화</TooltipContent>
                </Tooltip>

                {/* Project Selector (collapsed) */}
                <ProjectSelector collapsed />
              </div>
              <div className='flex flex-col items-center gap-2'>
                {BOTTOM_ICONS.map(({ icon: Icon, label, onClick }) => (
                  <Tooltip key={label}>
                    <TooltipTrigger asChild>
                      <Button
                        variant='ghost'
                        size='icon'
                        className='text-icon-default hover:text-icon-active h-9 w-9'
                        onClick={onClick}
                      >
                        <Icon className='h-5 w-5' />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side='right'>{label}</TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
