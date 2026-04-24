'use client';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import type { PullRequest } from '@/types/project';
import type { ArtifactDraft } from '@/stores/staging-store';
import {
  Check,
  FileDiff,
  GitBranch,
  GitMerge,
  GitPullRequest,
  PenSquare,
  Undo2,
  X,
} from 'lucide-react';

interface StagedChangesTrayProps {
  /** 패널 표시 여부 */
  open: boolean;
  onClose: () => void;

  unstaged: ArtifactDraft[];
  staged: ArtifactDraft[];
  openPRs: PullRequest[];
  prsLoading?: boolean;

  displayIdOf?: (artifactId: string) => string | undefined;

  // Unstaged 액션
  onStage: (artifactId: string) => void;
  onStageAll: () => void;
  onDiscardUnstaged: (artifactId: string) => void;

  // Staged 액션
  onUnstage: (artifactId: string) => void;
  onDiscardStaged: (artifactId: string) => void;
  onCreatePR: () => void;

  // PR 액션
  onApprovePR: (prId: string) => void;
  onRejectPR: (prId: string) => void;
  onMergePR: (prId: string) => void;
  onShowDiff: (pr: PullRequest) => void;
}

export function StagedChangesTray({
  open,
  onClose,
  unstaged,
  staged,
  openPRs,
  prsLoading,
  displayIdOf,
  onStage,
  onStageAll,
  onDiscardUnstaged,
  onUnstage,
  onDiscardStaged,
  onCreatePR,
  onApprovePR,
  onRejectPR,
  onMergePR,
  onShowDiff,
}: StagedChangesTrayProps) {
  if (!open) return null;

  const resolveLabel = (artifactId: string) =>
    displayIdOf?.(artifactId) ?? artifactId.slice(0, 8);

  return (
    <div className='border-line-primary bg-canvas-surface flex h-full w-80 flex-col border-l'>
      {/* Header */}
      <div className='border-line-primary flex shrink-0 items-center justify-between border-b px-3 py-2'>
        <span className='text-fg-primary text-xs font-semibold'>변경 내역</span>
        <Button
          variant='ghost'
          size='icon'
          className='text-fg-muted size-6'
          onClick={onClose}
        >
          <X className='size-3.5' />
        </Button>
      </div>

      <ScrollArea className='min-h-0 flex-1'>
        <div className='flex flex-col gap-4 p-3'>
          {/* Unstaged */}
          <Section
            title='Unstaged'
            count={unstaged.length}
            icon={PenSquare}
            trailing={
              unstaged.length > 0 ? (
                <Button
                  variant='ghost'
                  size='sm'
                  className='h-6 text-[10px]'
                  onClick={onStageAll}
                >
                  전체 Stage
                </Button>
              ) : null
            }
          >
            {unstaged.length === 0 ? (
              <EmptyHint>편집 후 저장하면 여기에 표시됩니다</EmptyHint>
            ) : (
              unstaged.map((d) => (
                <DraftRow
                  key={d.artifactId}
                  label={resolveLabel(d.artifactId)}
                  content={d.content}
                  originalContent={d.originalContent}
                  tone='amber'
                  actions={
                    <>
                      <IconButton
                        icon={Check}
                        title='Stage'
                        onClick={() => onStage(d.artifactId)}
                      />
                      <IconButton
                        icon={Undo2}
                        title='폐기'
                        onClick={() => onDiscardUnstaged(d.artifactId)}
                        destructive
                      />
                    </>
                  }
                />
              ))
            )}
          </Section>

          {/* Staged */}
          <Section
            title='Staged'
            count={staged.length}
            icon={GitBranch}
            trailing={
              staged.length > 0 ? (
                <Button size='sm' className='h-6 text-[10px]' onClick={onCreatePR}>
                  <GitPullRequest className='size-3' />
                  PR 생성
                </Button>
              ) : null
            }
          >
            {staged.length === 0 ? (
              <EmptyHint>Stage 된 변경이 없습니다</EmptyHint>
            ) : (
              staged.map((d) => (
                <DraftRow
                  key={d.artifactId}
                  label={resolveLabel(d.artifactId)}
                  content={d.content}
                  originalContent={d.originalContent}
                  tone='blue'
                  actions={
                    <>
                      <IconButton
                        icon={Undo2}
                        title='Unstage'
                        onClick={() => onUnstage(d.artifactId)}
                      />
                      <IconButton
                        icon={X}
                        title='폐기'
                        onClick={() => onDiscardStaged(d.artifactId)}
                        destructive
                      />
                    </>
                  }
                />
              ))
            )}
          </Section>

          {/* Open PRs */}
          <Section title='Open PRs' count={openPRs.length} icon={GitPullRequest}>
            {prsLoading ? (
              <div className='flex justify-center py-2'>
                <Spinner size='size-4' className='text-fg-muted' />
              </div>
            ) : openPRs.length === 0 ? (
              <EmptyHint>열린 PR 이 없습니다</EmptyHint>
            ) : (
              openPRs.map((pr) => (
                <div
                  key={pr.pr_id}
                  className='border-line-primary bg-canvas-primary/40 space-y-1.5 rounded-md border p-2'
                >
                  <div className='flex items-center gap-1.5 text-[11px]'>
                    <span className='text-fg-muted font-mono'>
                      {resolveLabel(pr.artifact_id)}
                    </span>
                    <span className='text-accent-primary font-medium'>
                      #{pr.pr_id.slice(0, 6)}
                    </span>
                    {pr.auto_generated && (
                      <span className='text-fg-muted text-[10px]'>auto</span>
                    )}
                  </div>
                  <p className='text-fg-primary line-clamp-2 text-xs leading-snug'>
                    {pr.title}
                  </p>
                  <div className='flex items-center gap-1'>
                    <Button
                      variant='ghost'
                      size='sm'
                      className='text-fg-secondary h-6 gap-1 px-2 text-[10px]'
                      onClick={() => onShowDiff(pr)}
                      title='변경 내용 보기'
                    >
                      <FileDiff className='size-3' />
                      변경
                    </Button>
                    <Button
                      variant='ghost'
                      size='sm'
                      className='h-6 gap-1 px-2 text-[10px] text-green-600'
                      onClick={() => onApprovePR(pr.pr_id)}
                    >
                      <Check className='size-3' />
                      승인
                    </Button>
                    <Button
                      variant='ghost'
                      size='sm'
                      className='h-6 gap-1 px-2 text-[10px] text-red-500'
                      onClick={() => onRejectPR(pr.pr_id)}
                    >
                      <X className='size-3' />
                      거절
                    </Button>
                    <Button
                      size='sm'
                      className='ml-auto h-6 gap-1 px-2 text-[10px]'
                      onClick={() => onMergePR(pr.pr_id)}
                    >
                      <GitMerge className='size-3' />
                      머지
                    </Button>
                  </div>
                </div>
              ))
            )}
          </Section>
        </div>
      </ScrollArea>
    </div>
  );
}

// ── 내부 UI 빌딩 블록 ────────────────────────────────────────────────────

interface SectionProps {
  title: string;
  count: number;
  icon: typeof PenSquare;
  trailing?: React.ReactNode;
  children: React.ReactNode;
}

function Section({ title, count, icon: Icon, trailing, children }: SectionProps) {
  return (
    <section className='flex flex-col gap-1.5'>
      <div className='flex items-center gap-1.5'>
        <Icon className='text-fg-muted size-3' />
        <span className='text-fg-secondary text-[10px] font-semibold tracking-wider uppercase'>
          {title}
        </span>
        <span className='text-fg-muted text-[10px] tabular-nums'>({count})</span>
        <div className='ml-auto'>{trailing}</div>
      </div>
      <div className='flex flex-col gap-1.5'>{children}</div>
    </section>
  );
}

function EmptyHint({ children }: { children: React.ReactNode }) {
  return <p className='text-fg-muted px-1 py-2 text-[11px]'>{children}</p>;
}

type RowTone = 'amber' | 'blue';

interface DraftRowProps {
  label: string;
  content: string;
  originalContent: string;
  tone: RowTone;
  actions?: React.ReactNode;
}

function DraftRow({ label, content, originalContent, tone, actions }: DraftRowProps) {
  const toneCls =
    tone === 'amber'
      ? 'border-amber-500/40 bg-amber-500/5'
      : 'border-blue-500/40 bg-blue-500/5';
  return (
    <div className={cn('rounded-md border p-2', toneCls)}>
      <div className='mb-1 flex items-center gap-1.5'>
        <span className='text-fg-secondary font-mono text-[11px] font-medium'>
          {label}
        </span>
        <div className='ml-auto flex items-center gap-0.5'>{actions}</div>
      </div>
      <p className='text-fg-primary line-clamp-2 text-xs leading-snug'>{content}</p>
      {originalContent && originalContent !== content && (
        <p className='text-fg-muted mt-1 line-clamp-1 text-[10px] line-through'>
          {originalContent}
        </p>
      )}
    </div>
  );
}

function IconButton({
  icon: Icon,
  title,
  onClick,
  destructive,
}: {
  icon: typeof PenSquare;
  title: string;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      type='button'
      title={title}
      onClick={onClick}
      className={cn(
        'text-fg-muted inline-flex size-5 items-center justify-center rounded transition-colors',
        destructive ? 'hover:bg-red-500/10 hover:text-red-500' : 'hover:bg-canvas-primary hover:text-fg-primary',
      )}
    >
      <Icon className='size-3' />
    </button>
  );
}
