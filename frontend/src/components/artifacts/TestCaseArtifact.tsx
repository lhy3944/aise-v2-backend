'use client';

import { FlaskConical, MessageSquare, Pencil } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  TestCaseEditor,
  TestCaseEditorActions,
  type TestCaseEditorPayload,
} from '@/components/artifacts/workspace/editor/TestCaseEditor';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { useOverlay } from '@/hooks/useOverlay';
import { cn } from '@/lib/utils';
import { artifactService } from '@/services/artifact-service';
import { useProjectStore } from '@/stores/project-store';
import type { Artifact } from '@/types/project';
import type {
  TestCaseContent,
  TestCasePriority,
  TestCaseType,
} from '@/types/testcase';

type TestCaseArtifact = Artifact<TestCaseContent>;

const PRIORITY_CONFIG: Record<
  TestCasePriority,
  { label: string; tone: string }
> = {
  high: { label: 'High', tone: 'text-red-600' },
  medium: { label: 'Medium', tone: 'text-amber-600' },
  low: { label: 'Low', tone: 'text-fg-muted' },
};

const TYPE_CONFIG: Record<TestCaseType, { label: string }> = {
  functional: { label: 'Functional' },
  non_functional: { label: 'Non-functional' },
  boundary: { label: 'Boundary' },
  negative: { label: 'Negative' },
};

export function TestCaseArtifact() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const projectId = currentProject?.project_id;

  const [artifacts, setArtifacts] = useState<TestCaseArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [priorityFilter, setPriorityFilter] = useState<TestCasePriority[]>([]);
  const [typeFilter, setTypeFilter] = useState<TestCaseType[]>([]);

  const overlay = useOverlay();

  const fetchList = useCallback(async () => {
    if (!projectId) return;
    try {
      const res = await artifactService.list(projectId, {
        artifact_type: 'testcase',
      });
      const items = res.artifacts as unknown as TestCaseArtifact[];
      const sorted = [...items].sort((a, b) =>
        a.display_id.localeCompare(b.display_id, undefined, {
          numeric: true,
          sensitivity: 'base',
        }),
      );
      setArtifacts(sorted);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    void fetchList();
  }, [projectId, fetchList]);

  const filtered = useMemo(
    () =>
      artifacts.filter((a) => {
        if (
          priorityFilter.length > 0 &&
          !priorityFilter.includes(a.content.priority)
        )
          return false;
        if (typeFilter.length > 0 && !typeFilter.includes(a.content.type))
          return false;
        return true;
      }),
    [artifacts, priorityFilter, typeFilter],
  );

  const handleEdit = useCallback(
    (artifact: TestCaseArtifact) => {
      if (!projectId) return;

      const submit = async (payload: TestCaseEditorPayload) => {
        try {
          const updated = await artifactService.update(
            projectId,
            artifact.artifact_id,
            {
              content: payload as unknown as Record<string, unknown>,
              title: payload.title,
            },
          );
          setArtifacts((prev) =>
            prev.map((a) =>
              a.artifact_id === updated.artifact_id
                ? (updated as unknown as TestCaseArtifact)
                : a,
            ),
          );
          overlay.closeModal();
        } catch {
          // 글로벌 핸들러
        }
      };

      overlay.modal({
        title: `테스트 케이스 편집 — ${artifact.display_id}`,
        size: 'lg',
        content: (
          <TestCaseEditor initial={artifact.content} onSubmit={submit} />
        ),
        footer: <TestCaseEditorActions onCancel={() => overlay.closeModal()} />,
      });
    },
    [projectId, overlay],
  );

  if (!projectId) return null;

  if (loading) {
    return (
      <div className='flex h-full items-center justify-center'>
        <Spinner size='size-6' className='text-fg-muted' />
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div className='flex h-full flex-col items-center justify-center gap-3 p-6 text-center'>
        <FlaskConical className='text-fg-muted size-10' />
        <div>
          <p className='text-fg-secondary text-sm font-medium'>
            테스트 케이스 없음
          </p>
          <p className='text-fg-muted mt-1 text-xs'>
            채팅에서 &ldquo;테스트 케이스 생성&rdquo;을 요청하면 SRS 기반으로
            자동 생성됩니다.
          </p>
        </div>
        <div className='text-fg-muted inline-flex items-center gap-1.5 text-[11px]'>
          <MessageSquare className='size-3' />
          예: &ldquo;SRS 기반으로 테스트케이스를 만들어줘&rdquo;
        </div>
      </div>
    );
  }

  const activeFilters = priorityFilter.length + typeFilter.length;

  return (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='border-line-primary flex items-center justify-between border-b px-4 py-2'>
        <span className='text-fg-primary text-xs font-semibold'>
          {filtered.length}/{artifacts.length}개 TC
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant='ghost' size='sm' className='h-7 gap-1.5 text-xs'>
              필터
              {activeFilters > 0 && (
                <Badge className='ml-0.5 h-4 min-w-4 rounded-full px-1 text-[10px]'>
                  {activeFilters}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align='end' className='w-48 text-xs'>
            <div className='text-fg-muted px-2 py-1 text-[10px] font-semibold tracking-wider uppercase'>
              우선순위
            </div>
            {(['high', 'medium', 'low'] as TestCasePriority[]).map((p) => (
              <DropdownMenuCheckboxItem
                key={p}
                checked={priorityFilter.includes(p)}
                onCheckedChange={(checked) =>
                  setPriorityFilter((prev) =>
                    checked ? [...prev, p] : prev.filter((x) => x !== p),
                  )
                }
                onSelect={(e) => e.preventDefault()}
                className='text-xs'
              >
                {PRIORITY_CONFIG[p].label}
              </DropdownMenuCheckboxItem>
            ))}
            <DropdownMenuSeparator />
            <div className='text-fg-muted px-2 py-1 text-[10px] font-semibold tracking-wider uppercase'>
              유형
            </div>
            {(
              [
                'functional',
                'non_functional',
                'boundary',
                'negative',
              ] as TestCaseType[]
            ).map((t) => (
              <DropdownMenuCheckboxItem
                key={t}
                checked={typeFilter.includes(t)}
                onCheckedChange={(checked) =>
                  setTypeFilter((prev) =>
                    checked ? [...prev, t] : prev.filter((x) => x !== t),
                  )
                }
                onSelect={(e) => e.preventDefault()}
                className='text-xs'
              >
                {TYPE_CONFIG[t].label}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* List */}
      <ScrollArea className='min-h-0 flex-1'>
        <div className='flex flex-col gap-2 p-3 pb-6'>
          {filtered.map((tc) => {
            const priorityCfg = PRIORITY_CONFIG[tc.content.priority];
            const typeCfg = TYPE_CONFIG[tc.content.type];
            return (
              <article
                key={tc.artifact_id}
                className='group border-line-primary hover:border-fg-muted/50 hover:bg-canvas-primary/30 space-y-2 rounded-lg border px-3.5 py-3 transition-colors'
              >
                <header className='flex items-center gap-2 text-[11px]'>
                  <span className='text-fg-secondary font-mono font-medium'>
                    {tc.display_id}
                  </span>
                  <span className='opacity-40'>·</span>
                  <span className={cn('font-medium', priorityCfg.tone)}>
                    {priorityCfg.label}
                  </span>
                  <span className='opacity-40'>·</span>
                  <span className='text-fg-muted'>{typeCfg.label}</span>
                  <Button
                    variant='ghost'
                    size='sm'
                    className='text-fg-secondary ml-auto h-6 gap-1 px-2 text-[10px] opacity-0 transition-opacity group-hover:opacity-100'
                    onClick={() => handleEdit(tc)}
                  >
                    <Pencil className='size-3' />
                    편집
                  </Button>
                </header>

                <h4 className='text-fg-primary text-sm font-semibold'>
                  {tc.content.title}
                </h4>

                {tc.content.precondition && tc.content.precondition !== '없음' && (
                  <div className='text-[11px]'>
                    <span className='text-fg-muted font-medium'>사전: </span>
                    <span className='text-fg-secondary'>
                      {tc.content.precondition}
                    </span>
                  </div>
                )}

                {tc.content.steps.length > 0 && (
                  <ol className='text-fg-primary space-y-0.5 text-xs'>
                    {tc.content.steps.map((step, idx) => (
                      <li key={idx} className='flex gap-1.5'>
                        <span className='text-fg-muted font-mono tabular-nums'>
                          {idx + 1}.
                        </span>
                        <span className='flex-1'>{step}</span>
                      </li>
                    ))}
                  </ol>
                )}

                {tc.content.expected_result && (
                  <div className='text-[11px]'>
                    <span className='text-fg-muted font-medium'>기대: </span>
                    <span className='text-fg-secondary'>
                      {tc.content.expected_result}
                    </span>
                  </div>
                )}
              </article>
            );
          })}
          {filtered.length === 0 && (
            <p className='text-fg-muted py-6 text-center text-xs'>
              필터 조건에 맞는 TC 가 없습니다.
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
