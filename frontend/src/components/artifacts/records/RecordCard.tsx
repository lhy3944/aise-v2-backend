import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import type {
  ArtifactRecord,
  ArtifactRecordStatus,
} from '@/types/project';
import { MoreHorizontal } from 'lucide-react';
import { memo } from 'react';

const CHIP_BASE =
  'inline-flex items-center justify-center rounded border border-line-primary py-1 px-1 text-[11px] font-medium leading-none';

const STATUS_CHIP: Record<
  ArtifactRecordStatus,
  { label: string; className: string }
> = {
  draft: {
    label: '초안',
    className: 'bg-secondary text-fg-muted',
  },
  approved: {
    label: '승인',
    className: 'text-green-700 dark:text-green-400',
  },
  excluded: {
    label: '제외',
    className: 'text-red-700 dark:text-red-400',
  },
};

export function ConfidenceIndicator({ score }: { score: number | null }) {
  if (score === null) return null;
  const pct = Math.round(score * 100);
  const dot =
    pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <span className='text-fg-muted inline-flex items-center gap-1 text-[11px] tabular-nums'>
      <span className={cn('size-1.5 rounded-full', dot)} />
      {pct}%
    </span>
  );
}

interface RecordCardProps {
  record: ArtifactRecord;
  draftText: string | null;
  onEdit: (record: ArtifactRecord) => void;
  onShowVersions: (record: ArtifactRecord) => void;
  onStatusChange: (record: ArtifactRecord, status: ArtifactRecordStatus) => void;
  onDelete: (artifactId: string) => void;
}

export const RecordCard = memo(function RecordCard({
  record,
  draftText,
  onEdit,
  onShowVersions,
  onStatusChange,
  onDelete,
}: RecordCardProps) {
  const displayContent = draftText ?? record.content;

  return (
    <div
      className={cn(
        'group border-line-primary hover:border-fg-muted/50 hover:bg-canvas-primary/30 space-y-1.5 rounded-lg border px-3.5 py-3 transition-colors',
        record.status === 'excluded' && 'opacity-50',
      )}
    >
      <div className='text-fg-muted flex items-center gap-2 text-[11px]'>
        <span className='text-fg-secondary font-medium'>
          {record.display_id}
        </span>
        {draftText !== null && (
          <span
            className={cn(
              CHIP_BASE,
              'text-violet-700 dark:text-violet-400',
            )}
          >
            unstaged
          </span>
        )}
        {record.is_auto_extracted === false && (
          <span className={cn(CHIP_BASE, 'text-fg-muted')}>
            수동 입력
          </span>
        )}
        {record.confidence_score != null && (
          <>
            <span className='opacity-40'>·</span>
            <ConfidenceIndicator
              score={record.confidence_score}
            />
          </>
        )}
        <span
          className={cn(
            CHIP_BASE,
            STATUS_CHIP[record.status].className,
          )}
        >
          {STATUS_CHIP[record.status].label}
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant='ghost'
              size='icon'
              className='text-fg-muted hover:text-fg-primary ml-auto size-7 shrink-0'
            >
              <MoreHorizontal className='size-4' />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align='end' className='w-44'>
            <DropdownMenuCheckboxItem
              checked={false}
              onCheckedChange={() => onEdit(record)}
              onSelect={(e) => e.preventDefault()}
            >
              편집
            </DropdownMenuCheckboxItem>
            {record.current_version_number != null &&
              record.current_version_number > 0 && (
                <DropdownMenuCheckboxItem
                  checked={false}
                  onCheckedChange={() =>
                    onShowVersions(record)
                  }
                  onSelect={(e) => e.preventDefault()}
                >
                  버전 히스토리
                  <span className='border-line-primary text-fg-muted ml-auto rounded-md border px-1.5 py-px text-[10px] font-medium'>
                    v{record.current_version_number}
                  </span>
                </DropdownMenuCheckboxItem>
              )}
            <DropdownMenuSeparator />
            {record.status !== 'approved' && (
              <DropdownMenuCheckboxItem
                checked={false}
                onCheckedChange={() =>
                  onStatusChange(record, 'approved')
                }
                onSelect={(e) => e.preventDefault()}
              >
                승인
              </DropdownMenuCheckboxItem>
            )}
            {record.status !== 'excluded' && (
              <DropdownMenuCheckboxItem
                checked={false}
                onCheckedChange={() =>
                  onStatusChange(record, 'excluded')
                }
                onSelect={(e) => e.preventDefault()}
              >
                제외
              </DropdownMenuCheckboxItem>
            )}
            {record.status === 'excluded' && (
              <DropdownMenuCheckboxItem
                checked={false}
                onCheckedChange={() =>
                  onStatusChange(record, 'draft')
                }
                onSelect={(e) => e.preventDefault()}
              >
                복원
              </DropdownMenuCheckboxItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuCheckboxItem
              checked={false}
              onCheckedChange={() =>
                onDelete(record.artifact_id)
              }
              onSelect={(e) => e.preventDefault()}
              className='text-destructive focus:text-destructive'
            >
              삭제
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <p className='text-fg-primary text-sm leading-relaxed'>
        {displayContent}
      </p>

      {record.source_document_name && (
        <p className='text-fg-muted truncate text-[11px]'>
          {record.source_document_name}
          {record.source_location && (
            <span className='opacity-70'>
              {' '}
              · {record.source_location}
            </span>
          )}
        </p>
      )}
    </div>
  );
});
