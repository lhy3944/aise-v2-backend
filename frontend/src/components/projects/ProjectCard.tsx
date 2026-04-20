'use client';

import { Badge } from '@/components/ui/badge';
import { MODULE_COLORS, MODULE_LABELS } from '@/constants/project';
import { formatRelativeTime } from '@/lib/format';
import { cn } from '@/lib/utils';
import type { Project } from '@/types/project';
import { BookOpen, Box, Clock, FolderOpen, LayoutList, Trash2, Users } from 'lucide-react';
import Link from 'next/link';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';

interface ProjectCardProps {
  project: Project;
  onDelete?: (projectId: string) => void;
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  return (
    <div className='group relative'>
      <Link
        href={`/projects/${project.project_id}`}
        className='border-line-primary bg-card/30 dark:bg-card group-hover:border-accent-primary/50 block rounded-lg border p-5 transition-all group-hover:shadow-md'
      >
        <div className='mb-3 flex items-center gap-2.5'>
          <div className='bg-accent-primary/10 flex size-9 shrink-0 items-center justify-center rounded-md'>
            <Box className='text-accent-primary size-4' />
          </div>
          <div className='min-w-0'>
            <h3 className='text-fg-primary group-hover:text-accent-primary truncate text-sm font-semibold transition-colors'>
              {project.name}
            </h3>
            <div className='mt-0.5 flex h-5 items-center gap-1'>
              {project.domain && (
                <Badge variant='outline' className='px-3 py-0.5 text-[10px]'>
                  {project.domain}
                </Badge>
              )}
              {project.product_type && (
                <Badge variant='outline' className='px-3 py-0.5 text-[10px]'>
                  {project.product_type}
                </Badge>
              )}
            </div>
          </div>
        </div>

        <p className='text-fg-secondary mb-3 line-clamp-2 min-h-[2lh] text-sm'>
          {project.description}
        </p>

        <div className='mb-3 flex flex-wrap gap-1.5'>
          {project.modules.map((mod) => (
            <Badge key={mod} variant='ghost' className={cn(MODULE_COLORS[mod], 'text-[10px]')}>
              {MODULE_LABELS[mod]}
            </Badge>
          ))}
        </div>

        <div className='text-fg-muted border-line-primary flex items-center justify-between border-t border-dotted pt-5 text-[12px]'>
          <div className='flex items-center gap-4'>
            <span className='flex items-center gap-1'>
              <Clock className='size-4' />
              {formatRelativeTime(project.updated_at)}
            </span>
            <span className='flex items-center gap-1'>
              <Users className='size-4' />
              {project.member_count}
            </span>
          </div>

          {project.readiness && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className='flex items-center gap-2 text-[12px]'>
                  <span className='flex items-center gap-1'>
                    <FolderOpen className={'size-4'} />
                    <span>{project.readiness.knowledge}</span>
                  </span>
                  <span className='flex items-center gap-1'>
                    <BookOpen className={'size-4'} />
                    <span>{project.readiness.glossary}</span>
                  </span>
                  <span className='flex items-center gap-1'>
                    <LayoutList className={'size-4'} />
                    <span>{project.readiness.sections}</span>
                  </span>
                  <span
                    className={cn(
                      'size-2.5 rounded-full',
                      project.readiness.is_ready ? 'bg-green-500' : 'bg-amber-500',
                    )}
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent>
                {project.readiness.is_ready ? '프로젝트 설정 완료' : '프로젝트 설정 미완료'}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </Link>

      {onDelete && (
        <Button
          variant={'ghost'}
          className='text-fg-muted absolute top-3 right-3 opacity-0 transition-opacity group-hover:opacity-100'
          onClick={() => onDelete(project.project_id)}
          aria-label='프로젝트 삭제'
        >
          <Trash2 className='size-4' />
        </Button>
      )}
    </div>
  );
}
