'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { headerTabsConfig } from '@/config/navigation';
import { cn } from '@/lib/utils';

export function HeaderTabs() {
  const pathname = usePathname();

  return (
    <div className='hidden items-center space-x-1 md:flex'>
      {headerTabsConfig.map((tab) => {
        const isActive = pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              'group hover:bg-secondary rounded-sm px-6 py-4 text-sm',
              isActive && 'bg-canvas-surface',
            )}
          >
            <div className='flex items-center gap-2 transition-transform duration-150 group-hover:-translate-y-0.5'>
              <tab.icon
                className={cn('h-5 w-5', isActive && 'text-accent-primary')}
              />
              <span className='font-normal tracking-wide'>{tab.label}</span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
