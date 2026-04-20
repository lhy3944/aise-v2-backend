'use client';

import { Box, Component, GitBranch, Grip, Shield, ShieldCheck, Workflow } from 'lucide-react';
import { AnimatedGridMenu, type GridMenuItem } from '@/components/overlay/AnimatedGridMenu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Button } from '../ui/button';

const apps = [
  { icon: Component, label: 'SAVE', desc: 'SAVE', iconColor: 'text-blue-500' },
  { icon: Box, label: 'BEE', desc: 'BEE', iconColor: 'text-blue-400' },
  {
    icon: ShieldCheck,
    label: 'VulDOC',
    desc: 'VulDOC',
    iconColor: 'text-teal-500',
  },
  {
    icon: GitBranch,
    label: 'FOSSLight',
    desc: 'FOSSLight',
    iconColor: 'text-teal-400',
  },
  {
    icon: Shield,
    label: '정적분석',
    desc: '보안 취약점 분석',
    iconColor: 'text-red-500',
  },
  {
    icon: Workflow,
    label: '코드리뷰',
    desc: '코드 리뷰 자동화',
    iconColor: 'text-purple-500',
  },
];

export function AppsDropdown({ contentClassName }: { contentClassName?: string }) {
  const menuItems: GridMenuItem[] = apps.map((app) => ({
    id: app.label,
    label: app.label,
    icon: app.icon,
    iconColor: app.iconColor,
    onClick: () => console.log(`Navigating to ${app.label}`),
  }));

  return (
    <AnimatedGridMenu
      items={menuItems}
      title='Apps'
      columns={3}
      contentClassName={contentClassName}
      trigger={
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant='ghost'
              className='text-icon-default hover:text-icon-active transition-colors'
            >
              <Grip className='h-5 w-5' />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Apps</TooltipContent>
        </Tooltip>
      }
    />
  );
}
