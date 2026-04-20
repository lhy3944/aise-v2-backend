'use client';

import { Menu } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useState } from 'react';
import { AppsDropdown } from '@/components/overlay/AppsDropdown';
import { LabsDialog, LabsTrigger } from '@/components/overlay/LabsDialog';
import { SettingsDialog } from '@/components/overlay/SettingsDialog';
import { Logo } from '@/components/shared/Logo';
import { ThemeToggle } from '@/components/shared/ThemeToggle';
import { Button } from '@/components/ui/button';
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from '@/components/ui/drawer';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { headerTabsConfig, SIDEBAR_ACTIONS } from '@/config/navigation';
import { cn } from '@/lib/utils';

export function MobileMenu() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const [labsOpen, setLabsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();

  const actionHandlers: Record<string, () => void> = {
    settings: () => setSettingsOpen(true),
  };

  const BOTTOM_ICONS = SIDEBAR_ACTIONS.filter((action) => action.id !== 'project').map(
    (action) => ({
      ...action,
      onClick: actionHandlers[action.id] ?? (() => {}),
    }),
  );

  return (
    <>
      <Drawer direction='left' open={open} onOpenChange={setOpen}>
        <DrawerTrigger asChild>
          <Button
            variant='ghost'
            size='icon'
            className='text-icon-default hover:text-icon-active hover:bg-canvas-surface lg:hidden'
          >
            <Menu className='h-5 w-5' />
            <span className='sr-only'>Toggle Menu</span>
          </Button>
        </DrawerTrigger>
        <DrawerContent className='border-r-line-primary bg-canvas-primary flex h-full w-[280px] flex-col p-0 sm:w-[320px]'>
          <DrawerHeader className='border-line-primary border-b p-4 text-left'>
            <DrawerTitle asChild>
              <div onClick={() => setOpen(false)} className='inline-block cursor-pointer'>
                <Logo showName={true} />
              </div>
            </DrawerTitle>
            <DrawerDescription />
          </DrawerHeader>
          {/* Navigation */}
          <div className='flex flex-1 flex-col py-4'>
            {headerTabsConfig.map((tab) => {
              const isActive = pathname.startsWith(tab.href);
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    'hover:bg-canvas-secondary hover:text-fg-primary flex items-center gap-3 px-6 py-4 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-canvas-surface text-accent-primary border-accent-primary border-r-4'
                      : 'text-fg-secondary',
                  )}
                >
                  <tab.icon className={cn('h-5 w-5', isActive && 'text-accent-primary')} />
                  {tab.label}
                </Link>
              );
            })}
          </div>

          {/* Bottom */}
          <div className='border-line-primary flex items-center gap-2 border-t p-4'>
            {BOTTOM_ICONS.map(({ id, icon: Icon, label, onClick }) => (
              <Tooltip key={id}>
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
                <TooltipContent side='top'>{label}</TooltipContent>
              </Tooltip>
            ))}
            <div className='ml-auto flex items-center gap-2'>
              <AppsDropdown contentClassName='fixed bottom-20 left-4 right-4 !w-auto origin-bottom' />
              <LabsTrigger onClick={() => setLabsOpen(true)} />
              <ThemeToggle
                checked={resolvedTheme === 'dark'}
                onCheckedChange={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
              />
            </div>
          </div>
        </DrawerContent>
      </Drawer>

      <LabsDialog open={labsOpen} onOpenChange={setLabsOpen} />
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
