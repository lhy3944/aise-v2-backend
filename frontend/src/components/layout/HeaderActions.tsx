'use client';

import { AppsDropdown } from '@/components/overlay/AppsDropdown';
import { LabsDialog, LabsTrigger } from '@/components/overlay/LabsDialog';
import { ProfileDropdown } from '@/components/overlay/ProfileDropdown';
import { SearchDialog } from '@/components/overlay/SearchDialog';
import { SettingsDialog } from '@/components/overlay/SettingsDialog';
import { ThemeToggle } from '@/components/shared/ThemeToggle';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { usePanelStore } from '@/stores/panel-store';
import { Bell, Fullscreen, Search } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useState } from 'react';
import { Button } from '../ui/button';
import { Separator } from '../ui/separator';
import { NotificationPanel } from './NotificationPanel';

interface HeaderActionsProps {
  showLayoutToggle?: boolean;
}

export function HeaderActions({ showLayoutToggle = false }: HeaderActionsProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const toggleNotification = usePanelStore((s) => s.toggleNotification);
  const toggleFullWidth = usePanelStore((s) => s.toggleFullWidth);
  const notificationOpen = usePanelStore((s) => s.notificationOpen);
  const fullWidthMode = usePanelStore((s) => s.fullWidthMode);

  const [searchOpen, setSearchOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsInitialTab, setSettingsInitialTab] = useState<string | undefined>(undefined);
  const [labsOpen, setLabsOpen] = useState(false);

  const openSettings = (tab = 'general') => {
    setSettingsInitialTab(tab);
    setSettingsOpen(true);
  };

  return (
    <>
      <div className='flex items-center gap-1'>
        {/* 검색 */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => setSearchOpen(true)}
              variant={'ghost'}
              className='text-icon-default hover:text-icon-active transition-colors'
            >
              <Search className='h-5 w-5' />
            </Button>
          </TooltipTrigger>
          <TooltipContent>검색 (Ctrl+K)</TooltipContent>
        </Tooltip>

        {/* 알림 */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={(e) => {
                (e.currentTarget as HTMLElement).blur();
                toggleNotification();
              }}
              variant={'ghost'}
              className={`transition-colors ${notificationOpen ? 'text-icon-active' : 'text-icon-default hover:text-icon-active'}`}
            >
              <Bell className='h-5 w-5' />
              <span className='pointer-events-none absolute mb-5 ml-3 h-[8px] w-[7px] rounded-full bg-red-500 px-1 leading-none'></span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>알림</TooltipContent>
        </Tooltip>

        {/* Apps - Hide on mobile */}
        <div className='hidden lg:block'>
          <AppsDropdown />
        </div>

        {/* Labs - Hide on mobile */}
        <div className='hidden lg:block'>
          <LabsTrigger onClick={() => setLabsOpen(true)} />
        </div>

        <Separator
          orientation='vertical'
          className='mx-2 hidden data-[orientation=vertical]:h-6 md:block'
        />

        {/* 레이아웃 토글 - Hide on mobile */}
        <div className='hidden items-center lg:flex'>
          {showLayoutToggle && (
            <div className='hidden md:block'>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={toggleFullWidth}
                    variant={'ghost'}
                    className={`transition-colors ${fullWidthMode ? 'text-icon-active' : 'text-icon-default hover:text-icon-active'}`}
                  >
                    <Fullscreen
                      className='h-5 w-5'
                      fill={fullWidthMode ? 'currentColor' : 'transparent'}
                    />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>전체 레이아웃</TooltipContent>
              </Tooltip>
            </div>
          )}

          {/* 테마토글 */}
          <ThemeToggle
            className='hidden md:mx-2 md:flex'
            checked={resolvedTheme === 'dark'}
            onCheckedChange={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
          />
        </div>

        {/* 프로필 */}
        <ProfileDropdown
          onSettingsOpen={() => openSettings()}
          onProfileOpen={() => openSettings('account')}
        />
      </div>

      {/* Dialogs */}
      <SearchDialog open={searchOpen} onOpenChange={setSearchOpen} />
      <SettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        initialTab={settingsInitialTab}
      />
      <LabsDialog open={labsOpen} onOpenChange={setLabsOpen} />
      <NotificationPanel />
    </>
  );
}
