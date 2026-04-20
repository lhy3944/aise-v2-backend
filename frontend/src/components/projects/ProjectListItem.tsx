'use client';

import { Box, Clock, Trash2, Users } from 'lucide-react';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MODULE_COLORS, MODULE_LABELS } from '@/constants/project';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/lib/format';
import type { Project } from '@/types/project';

interface ProjectListItemProps {
  project: Project;
  onDelete?: (projectId: string) => void;
}

export function ProjectListItem({ project, onDelete }: ProjectListItemProps) {
  return (
    <Link
      href={`/projects/${project.project_id}`}
      className='group border-line-primary bg-card hover:border-accent-primary/50 flex items-center gap-4 rounded-lg border px-5 py-3.5 transition-all'
    >
      <div className='bg-accent-primary/10 flex size-9 shrink-0 items-center justify-center rounded-md'>
        <Box className='text-accent-primary size-4' />
      </div>

      <div className='min-w-0 flex-1'>
        <div className='flex items-center gap-1.5'>
          <h3 className='text-fg-primary group-hover:text-accent-primary truncate text-sm font-semibold transition-colors'>
            {project.name}
          </h3>
          {project.domain && (
            <Badge variant='outline' className='hidden shrink-0 px-2 py-0 text-[10px] sm:inline-flex'>
              {project.domain}
            </Badge>
          )}
          {project.product_type && (
            <Badge variant='outline' className='hidden shrink-0 px-2 py-0 text-[10px] sm:inline-flex'>
              {project.product_type}
            </Badge>
          )}
        </div>

        {/* 모바일: 설명 대신 모듈 뱃지 + 메타 정보 표시 */}
        <div className='mt-1 flex flex-col gap-0.5 sm:hidden'>
          <div className='flex items-center gap-1'>
            {project.modules.map((mod) => (
              <Badge key={mod} variant='ghost' className={cn(MODULE_COLORS[mod], 'px-1.5 py-0 text-[10px]')}>
                {MODULE_LABELS[mod]}
              </Badge>
            ))}
          </div>
          <span className='text-fg-muted text-[11px]'>{formatRelativeTime(project.updated_at)}</span>
        </div>

        {/* 태블릿+: 설명 텍스트 */}
        {project.description && (
          <p className='text-fg-secondary mt-0.5 hidden truncate text-xs sm:block'>{project.description}</p>
        )}
      </div>

      <div className='hidden shrink-0 items-center gap-1.5 sm:flex'>
        {project.modules.map((mod) => (
          <Badge key={mod} variant='ghost' className={MODULE_COLORS[mod]}>
            {MODULE_LABELS[mod]}
          </Badge>
        ))}
      </div>

      <div className='text-fg-muted hidden shrink-0 items-center gap-4 text-xs lg:flex'>
        <span className='flex items-center gap-1'>
          <Clock className='size-3.5' />
          {formatRelativeTime(project.updated_at)}
        </span>
        <span className='flex items-center gap-1'>
          <Users className='size-3.5' />
          {project.member_count}
        </span>
      </div>

      {onDelete && (
        <Button
          variant='ghost'
          className='text-fg-muted shrink-0 opacity-0 transition-opacity group-hover:opacity-100'
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete(project.project_id);
          }}
          aria-label='프로젝트 삭제'
        >
          <Trash2 className='size-4' />
        </Button>
      )}
    </Link>
  );
}
