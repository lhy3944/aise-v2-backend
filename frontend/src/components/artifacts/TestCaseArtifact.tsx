'use client';

import {
  FileText,
  FlaskConical,
  Link2,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ArtifactEmptyGuide } from '@/components/artifacts/ArtifactEmptyGuide';
import {
  TestCaseEditor,
  TestCaseEditorActions,
  type TestCaseEditorPayload,
} from '@/components/artifacts/workspace/editor/TestCaseEditor';
import { lineageInline } from '@/components/artifacts/workspace/lineagePreview';
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
import { MISSING_SRS_MESSAGE } from '@/constants/artifact-messages';
import { useImpact } from '@/hooks/useImpact';
import { useOverlay } from '@/hooks/useOverlay';
import { showToast } from '@/lib/toast';
import { cn } from '@/lib/utils';
import { artifactService } from '@/services/artifact-service';
import { srsService } from '@/services/srs-service';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { useChatStore } from '@/stores/chat-store';
import { useProjectStore } from '@/stores/project-store';
import { EMPTY_BUCKET, useStagingStore } from '@/stores/staging-store';
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

const EMPTY_TESTCASE_GUIDES = [
  {
    icon: FileText,
    title: 'SRS 기반 생성',
    description: '완료된 SRS의 기능 요구사항을 테스트 관점으로 전환합니다.',
  },
  {
    icon: FlaskConical,
    title: '검증 시나리오 정리',
    description: '우선순위, 유형, 사전조건, 절차, 기대결과를 구조화합니다.',
  },
  {
    icon: Link2,
    title: '상위 문서 추적',
    description: '생성된 테스트케이스는 기반 SRS와 연결됩니다.',
  },
];

export function TestCaseArtifact() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const projectId = currentProject?.project_id;

  const [artifacts, setArtifacts] = useState<TestCaseArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [priorityFilter, setPriorityFilter] = useState<TestCasePriority[]>([]);
  const [typeFilter, setTypeFilter] = useState<TestCaseType[]>([]);
  const [hasSrsDocument, setHasSrsDocument] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const setInputValue = useChatStore((s) => s.setInputValue);

  const overlay = useOverlay();

  const refreshNonce = useArtifactRefreshStore((s) => s.nonce.testcase);
  const srsRefreshNonce = useArtifactRefreshStore((s) => s.nonce.srs);

  // 출처 보기 → SRS 탭으로 이동
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const setPendingFocus = useArtifactStore((s) => s.setPendingFocus);

  // Phase F: stale 판정 — TC 의 source 인 SRS 가 갱신되면 stale.
  const { staleByArtifactId } = useImpact(projectId);

  const unstagedArtifacts = useStagingStore(
    (s) =>
      (projectId && s.byProject[projectId]?.unstaged) || EMPTY_BUCKET.unstaged,
  );
  const stagedArtifacts = useStagingStore(
    (s) => (projectId && s.byProject[projectId]?.staged) || EMPTY_BUCKET.staged,
  );
  const _setDraft = useStagingStore((s) => s.setDraft);
  const _discardDraft = useStagingStore((s) => s.discardDraft);
  const setArtifactDraft = useCallback(
    (draft: Parameters<typeof _setDraft>[1]) => {
      if (!projectId) return;
      _setDraft(projectId, draft);
    },
    [_setDraft, projectId],
  );
  const discardArtifactDraft = useCallback(
    (artifactId: string) => {
      if (!projectId) return;
      _discardDraft(projectId, artifactId);
    },
    [_discardDraft, projectId],
  );

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    Promise.all([
      artifactService.list(projectId, { artifact_type: 'testcase' }),
      srsService.list(projectId),
    ])
      .then(([artifactRes, srsRes]) => {
        if (cancelled) return;
        const items = artifactRes.artifacts as unknown as TestCaseArtifact[];
        const sorted = [...items].sort((a, b) =>
          a.display_id.localeCompare(b.display_id, undefined, {
            numeric: true,
            sensitivity: 'base',
          }),
        );
        setArtifacts(sorted);
        setHasSrsDocument(srsRes.documents.length > 0);
        setErrorMessage(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, refreshNonce, srsRefreshNonce]);

  const handlePrepareTestcasePrompt = useCallback(() => {
    if (!hasSrsDocument) {
      setErrorMessage(MISSING_SRS_MESSAGE);
      showToast.error(MISSING_SRS_MESSAGE);
      return;
    }

    setErrorMessage(null);
    setInputValue('SRS 기반으로 테스트케이스를 만들어줘');
    requestAnimationFrame(() => {
      const textarea = document.querySelector<HTMLTextAreaElement>(
        'textarea[name="message"]',
      );
      textarea?.focus();
    });
  }, [hasSrsDocument, setInputValue]);

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

      const existing = unstagedArtifacts[artifact.artifact_id];
      // 기존 드래프트가 있으면 그 본문을, 없으면 server 원본을 editor 초기값으로.
      const initialContent =
        (existing?.content as unknown as TestCaseContent) ?? artifact.content;

      const submit = (payload: TestCaseEditorPayload) => {
        // 직접 update 금지 — staging-store 의 unstaged 버퍼로만 누적.
        // 실제 서버 반영은 ChangesWorkspaceModal 의 PR 워크플로우로.
        setArtifactDraft({
          artifactId: artifact.artifact_id,
          artifactKind: 'testcase',
          content: payload as unknown as Record<string, unknown>,
          originalContent: artifact.content as unknown as Record<
            string,
            unknown
          >,
          editedAt: new Date().toISOString(),
          displayLabel: artifact.display_id,
        });
        overlay.closeModal();
      };

      overlay.modal({
        title: `테스트 케이스 편집 — ${artifact.display_id}`,
        description:
          '저장해도 서버에는 아직 반영되지 않습니다 (Unstaged 드래프트로 누적됩니다)',
        size: 'lg',
        content: <TestCaseEditor initial={initialContent} onSubmit={submit} />,
        footer: <TestCaseEditorActions onCancel={() => overlay.closeModal()} />,
      });
    },
    [projectId, overlay, unstagedArtifacts, setArtifactDraft],
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
      <ArtifactEmptyGuide
        icon={FlaskConical}
        title='테스트케이스가 존재하지 않습니다.'
        description='완료된 SRS로 검증 시나리오를 생성합니다.'
        guides={EMPTY_TESTCASE_GUIDES}
        errorMessage={errorMessage}
        action={
          <Button
            size='sm'
            className='h-8 gap-1.5 px-3 text-xs'
            onClick={handlePrepareTestcasePrompt}
          >
            <MessageSquare className='size-3.5' />
            Testcase 생성
          </Button>
        }
      />
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
        <div className='flex items-center gap-1.5'>
          {(() => {
            // TC 가 다수 SRS 를 참조하는 경우는 드물어, 첫 TC 의 SRS source 를 대표값으로 사용.
            const firstTc = artifacts[0];
            const srsRef = firstTc?.current_source_artifact_versions?.srs?.[0];
            const versionId = srsRef?.version_id;
            if (!versionId) return null;
            return (
              <Button
                variant='ghost'
                size='sm'
                className='h-7 gap-1.5 text-xs'
                onClick={() => {
                  setPendingFocus({ kind: 'srs', versionId });
                  setActiveTab('srs');
                }}
              >
                <Link2 className='size-3.5' />
                출처 보기
              </Button>
            );
          })()}
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
      </div>

      {/* List */}
      <ScrollArea className='min-h-0 flex-1'>
        <div className='flex flex-col gap-2 p-3 pb-6'>
          {filtered.map((tc) => {
            // 드래프트가 있으면 로컬 편집본을 우선 표시 (record 패턴과 동일).
            const unstagedDraft = unstagedArtifacts[tc.artifact_id];
            const stagedDraft = stagedArtifacts[tc.artifact_id];
            const draftContent =
              (unstagedDraft?.content as unknown as
                | TestCaseContent
                | undefined) ??
              (stagedDraft?.content as unknown as TestCaseContent | undefined);
            const display = draftContent ?? tc.content;
            const priorityCfg = PRIORITY_CONFIG[display.priority];
            const typeCfg = TYPE_CONFIG[display.type];
            return (
              <article
                key={tc.artifact_id}
                className='group border-line-primary hover:border-fg-muted/50 hover:bg-canvas-primary/30 space-y-2 rounded-lg border px-3.5 py-3 transition-colors'
              >
                <header className='flex items-center gap-2 text-[11px]'>
                  <span className='text-fg-secondary font-mono font-medium'>
                    {tc.display_id}
                  </span>
                  {(unstagedDraft || stagedDraft) && (
                    <span
                      className={cn(
                        'inline-block size-1.5 shrink-0 rounded-full',
                        unstagedDraft ? 'bg-amber-500' : 'bg-blue-500',
                      )}
                      title={unstagedDraft ? 'Unstaged 변경' : 'Staged 변경'}
                    />
                  )}
                  <span className='opacity-40'>·</span>
                  <span className={cn('font-medium', priorityCfg.tone)}>
                    {priorityCfg.label}
                  </span>
                  <span className='opacity-40'>·</span>
                  <span className='text-fg-muted'>{typeCfg.label}</span>
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
                    <DropdownMenuContent align='end' className='w-40'>
                      <DropdownMenuCheckboxItem
                        checked={false}
                        onCheckedChange={() => handleEdit(tc)}
                        onSelect={(e) => e.preventDefault()}
                        className='gap-2'
                      >
                        <Pencil className='size-3.5' />
                        편집
                      </DropdownMenuCheckboxItem>
                      {unstagedDraft && (
                        <DropdownMenuCheckboxItem
                          checked={false}
                          onCheckedChange={() =>
                            discardArtifactDraft(tc.artifact_id)
                          }
                          onSelect={(e) => e.preventDefault()}
                          className='gap-2 text-destructive focus:text-destructive'
                        >
                          <Trash2 className='size-3.5' />
                          드래프트 폐기
                        </DropdownMenuCheckboxItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </header>

                <h4 className='text-fg-primary text-sm font-semibold'>
                  {display.title}
                </h4>

                {display.precondition && display.precondition !== '없음' && (
                  <div className='text-[11px]'>
                    <span className='text-fg-muted font-medium'>사전: </span>
                    <span className='text-fg-secondary'>
                      {display.precondition}
                    </span>
                  </div>
                )}

                {display.steps.length > 0 && (
                  <ol className='text-fg-primary space-y-0.5 text-xs'>
                    {display.steps.map((step, idx) => (
                      <li key={idx} className='flex gap-1.5'>
                        <span className='text-fg-muted font-mono tabular-nums'>
                          {idx + 1}.
                        </span>
                        <span className='flex-1'>{step}</span>
                      </li>
                    ))}
                  </ol>
                )}

                {display.expected_result && (
                  <div className='text-[11px]'>
                    <span className='text-fg-muted font-medium'>기대: </span>
                    <span className='text-fg-secondary'>
                      {display.expected_result}
                    </span>
                  </div>
                )}

                {(() => {
                  const inline = lineageInline(
                    tc.current_source_artifact_versions,
                  );
                  if (!inline) return null;
                  return (
                    <span className='bg-muted text-fg-muted inline-block rounded px-2 py-0.5 text-[10px] font-medium whitespace-nowrap'>
                      {inline}
                    </span>
                  );
                })()}
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
