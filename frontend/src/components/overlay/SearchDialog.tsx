'use client';

import { Box, Clock, X } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  SEARCH_ACTION_ITEMS,
  SEARCH_NAVIGATION_ITEMS,
} from '@/config/search-commands';
import type { RecentSearchItem } from '@/stores/search-store';
import { useSearchStore } from '@/stores/search-store';
import { useProjectStore } from '@/stores/project-store';

interface SearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SearchDialog({ open, onOpenChange }: SearchDialogProps) {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const [query, setQuery] = useState('');

  const projects = useProjectStore((s) => s.projects);
  const recentItems = useSearchStore((s) => s.recentItems);
  const addRecentItem = useSearchStore((s) => s.addRecentItem);
  const removeRecentItem = useSearchStore((s) => s.removeRecentItem);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) setQuery('');
      onOpenChange(nextOpen);
    },
    [onOpenChange],
  );

  const select = useCallback(
    (item: RecentSearchItem, href?: string) => {
      addRecentItem(item);
      if (href) router.push(href);
      handleOpenChange(false);
    },
    [addRecentItem, router, handleOpenChange],
  );

  const handleNavigationSelect = useCallback(
    (nav: (typeof SEARCH_NAVIGATION_ITEMS)[number]) => {
      select(
        { id: nav.id, label: nav.label, type: 'navigation', href: nav.href },
        nav.href,
      );
    },
    [select],
  );

  const handleProjectSelect = useCallback(
    (project: { project_id: string; name: string }) => {
      const href = `/projects/${project.project_id}`;
      select(
        { id: project.project_id, label: project.name, type: 'project', href },
        href,
      );
    },
    [select],
  );

  const handleActionSelect = useCallback(
    (action: (typeof SEARCH_ACTION_ITEMS)[number]) => {
      if (action.actionId === 'toggle-theme') {
        setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
        handleOpenChange(false);
        return;
      }
      if (action.href) {
        select(
          {
            id: action.id,
            label: action.label,
            type: 'action',
            href: action.href,
          },
          action.href,
        );
      }
    },
    [select, handleOpenChange, setTheme, resolvedTheme],
  );

  const handleRecentSelect = useCallback(
    (item: RecentSearchItem) => {
      if (item.href) router.push(item.href);
      handleOpenChange(false);
    },
    [router, handleOpenChange],
  );

  return (
    <CommandDialog
      open={open}
      onOpenChange={handleOpenChange}
      title='검색'
      description='페이지, 프로젝트, 명령어를 검색하세요'
      className='sm:max-w-[720px]'
      showCloseButton={false}
    >
      <CommandInput
        placeholder='검색어를 입력하세요...'
        value={query}
        onValueChange={setQuery}
      />
      <CommandList className='max-h-[420px]'>
        <CommandEmpty>
          <span className='text-fg-muted text-sm'>검색 결과가 없습니다</span>
        </CommandEmpty>

        {!query && recentItems.length > 0 && (
          <>
            <CommandGroup heading='최근 검색'>
              {recentItems.map((item) => (
                <CommandItem
                  key={item.id}
                  value={`recent-${item.label}`}
                  onSelect={() => handleRecentSelect(item)}
                >
                  <Clock className='text-fg-muted h-4 w-4 shrink-0' />
                  <span>{item.label}</span>
                  <button
                    className='text-fg-muted hover:text-fg-primary ml-auto rounded p-0.5'
                    onClick={(e) => {
                      e.stopPropagation();
                      removeRecentItem(item.id);
                    }}
                  >
                    <X className='h-3 w-3' />
                  </button>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        <CommandGroup heading='페이지'>
          {SEARCH_NAVIGATION_ITEMS.map((item) => (
            <CommandItem
              key={item.id}
              value={item.label}
              keywords={item.keywords}
              onSelect={() => handleNavigationSelect(item)}
            >
              <item.icon className='text-fg-muted h-4 w-4 shrink-0' />
              <span>{item.label}</span>
            </CommandItem>
          ))}
        </CommandGroup>

        {projects.length > 0 && (
          <CommandGroup heading='프로젝트'>
            {projects.map((project) => (
              <CommandItem
                key={project.project_id}
                value={`project-${project.name}`}
                keywords={[project.description, project.domain].filter(
                  (v): v is string => !!v,
                )}
                onSelect={() => handleProjectSelect(project)}
              >
                <Box className='text-fg-muted h-4 w-4 shrink-0' />
                <span>{project.name}</span>
                {project.domain && (
                  <span className='text-fg-muted ml-auto text-xs'>
                    {project.domain}
                  </span>
                )}
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        <CommandGroup heading='빠른 실행'>
          {SEARCH_ACTION_ITEMS.map((item) => (
            <CommandItem
              key={item.id}
              value={item.label}
              keywords={item.keywords}
              onSelect={() => handleActionSelect(item)}
            >
              <item.icon className='text-fg-muted h-4 w-4 shrink-0' />
              <span>{item.label}</span>
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
