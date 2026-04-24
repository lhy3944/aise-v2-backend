'use client';

import { ChangesWorkspaceModal } from '@/components/artifacts/workspace/ChangesWorkspaceModal';
import {
  ArtifactRecordEditor,
  ArtifactRecordEditorActions,
  type ArtifactRecordEditorValues,
} from '@/components/artifacts/workspace/editor/ArtifactRecordEditor';
import { WorkspaceStatusBar } from '@/components/artifacts/workspace/WorkspaceStatusBar';
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
import { artifactRecordService } from '@/services/artifact-record-service';
import { artifactService } from '@/services/artifact-service';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { usePrStore } from '@/stores/pr-store';
import { EMPTY_BUCKET, useStagingStore } from '@/stores/staging-store';
import type {
  ArtifactRecord,
  ArtifactRecordCreate,
  ArtifactRecordStatus,
} from '@/types/project';
import {
  Check,
  CheckCircle2,
  Database,
  FileText,
  Filter,
  MinusCircle,
  Pencil,
  Trash2,
  XCircle,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface ArtifactRecordsPanelProps {
  projectId: string;
}

const STATUS_CONFIG: Record<
  ArtifactRecordStatus,
  { icon: typeof CheckCircle2; label: string; color: string }
> = {
  draft: { icon: FileText, label: '초안', color: 'text-gray-500' },
  approved: { icon: CheckCircle2, label: '승인', color: 'text-green-600' },
  excluded: { icon: MinusCircle, label: '제외', color: 'text-red-500' },
};

function ConfidenceIndicator({ score }: { score: number | null }) {
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

export function ArtifactRecordsPanel({ projectId }: ArtifactRecordsPanelProps) {
  const [records, setRecords] = useState<ArtifactRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [sectionFilters, setSectionFilters] = useState<string[]>([]);

  const extracting = useArtifactRecordStore((s) => s.extracting);
  const candidates = useArtifactRecordStore((s) => s.candidates);
  const extractError = useArtifactRecordStore((s) => s.extractError);
  const clearCandidates = useArtifactRecordStore((s) => s.clearCandidates);
  const refreshNonce = useArtifactRecordStore((s) => s.refreshNonce);
  const [selectedCandidates, setSelectedCandidates] = useState<Set<number>>(
    new Set(),
  );
  const [approving, setApproving] = useState(false);

  // 프로젝트별 bucket — 카운트 및 레코드 편집 UI 용으로만 구독.
  // stage/unstage/discard/PR actions 는 ChangesWorkspaceModal 이 직접 담당.
  const unstagedArtifacts = useStagingStore(
    (s) => s.byProject[projectId]?.unstaged ?? EMPTY_BUCKET.unstaged,
  );
  const stagedArtifacts = useStagingStore(
    (s) => s.byProject[projectId]?.staged ?? EMPTY_BUCKET.staged,
  );
  const _setDraft = useStagingStore((s) => s.setDraft);
  const _discardDraft = useStagingStore((s) => s.discardDraft);
  const setArtifactDraft = useCallback(
    (draft: Parameters<typeof _setDraft>[1]) => _setDraft(projectId, draft),
    [_setDraft, projectId],
  );
  const discardArtifactDraft = useCallback(
    (artifactId: string) => _discardDraft(projectId, artifactId),
    [_discardDraft, projectId],
  );

  // PR 목록은 WorkspaceStatusBar 의 Open PR 카운트에만 필요.
  // loading/refresh/update 는 ChangesWorkspaceModal 로 이관.
  const openPRs = usePrStore((s) => s.openPRs);
  const setOpenPRs = usePrStore((s) => s.setOpenPRs);
  const setPrLoading = usePrStore((s) => s.setLoading);
  const prRefreshNonce = usePrStore((s) => s.refreshNonce);

  const overlay = useOverlay();

  const fetchRecords = useCallback(async () => {
    try {
      const res = await artifactRecordService.list(projectId);
      setRecords(res.records);
    } catch {
      // 글로벌 핸들링
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchRecords();
  }, [fetchRecords, refreshNonce]);

  // Open PRs 로딩
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setPrLoading(true);
      try {
        const res = await artifactService.listPRs(projectId, 'open');
        if (!cancelled) setOpenPRs(res.pull_requests);
      } catch {
        if (!cancelled) setOpenPRs([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, prRefreshNonce, setOpenPRs, setPrLoading]);

  // 섹션 목록 추출
  const sections = Array.from(
    new Map(
      records
        .filter((r) => r.section_id && r.section_name)
        .map((r) => [r.section_id!, r.section_name!]),
    ),
  );

  // 섹션별 그룹핑 (클라이언트 필터링)
  const filteredRecords =
    sectionFilters.length === 0
      ? records
      : records.filter(
          (r) => r.section_id && sectionFilters.includes(r.section_id),
        );

  const grouped = filteredRecords.reduce<Record<string, ArtifactRecord[]>>(
    (acc, r) => {
      const key = r.section_name || '미분류';
      if (!acc[key]) acc[key] = [];
      acc[key].push(r);
      return acc;
    },
    {},
  );

  const handleStatusChange = useCallback(
    async (record: ArtifactRecord, status: ArtifactRecordStatus) => {
      try {
        const updated = await artifactRecordService.updateStatus(
          projectId,
          record.artifact_id,
          status,
        );
        setRecords((prev) =>
          prev.map((r) =>
            r.artifact_id === updated.artifact_id ? updated : r,
          ),
        );
      } catch {
        // 글로벌 핸들링
      }
    },
    [projectId],
  );

  const handleDelete = useCallback(
    async (artifactId: string) => {
      try {
        await artifactRecordService.delete(projectId, artifactId);
        setRecords((prev) => prev.filter((r) => r.artifact_id !== artifactId));
        discardArtifactDraft(artifactId);
      } catch {
        // 글로벌 핸들링
      }
    },
    [projectId, discardArtifactDraft],
  );

  const handleEdit = useCallback(
    (record: ArtifactRecord) => {
      const existing = unstagedArtifacts[record.artifact_id];
      const handleSubmit = (values: ArtifactRecordEditorValues) => {
        // 원본 대비 변경이 없으면 드래프트 자체를 제거 — 불필요한 unstaged 표기 방지.
        if (values.content.trim() === record.content.trim()) {
          discardArtifactDraft(record.artifact_id);
        } else {
          setArtifactDraft({
            artifactId: record.artifact_id,
            content: values.content,
            originalContent: record.content,
            editedAt: new Date().toISOString(),
          });
        }
        overlay.closeModal();
      };

      overlay.modal({
        title: '레코드 편집',
        description:
          '저장해도 서버에는 아직 반영되지 않습니다 — Unstaged 드래프트로 누적됩니다.',
        size: 'md',
        content: (
          <ArtifactRecordEditor
            record={record}
            draftContent={existing?.content}
            onSubmit={handleSubmit}
          />
        ),
        footer: (
          <ArtifactRecordEditorActions
            hasDraft={!!existing}
            onCancel={() => overlay.closeModal()}
            onDiscard={() => {
              discardArtifactDraft(record.artifact_id);
              overlay.closeModal();
            }}
          />
        ),
      });
    },
    [overlay, unstagedArtifacts, setArtifactDraft, discardArtifactDraft],
  );

  // ── PR 워크플로우 ────────────────────────────────────────────────────
  // PR 생성 / 승인 / 거절 / 머지 / diff 보기 + stage/unstage/discard 핸들러는
  // 모두 ChangesWorkspaceModal 로 이관 (modal 내부에서 store 를 직접 구독해
  // 실시간 반영). 여기서는 모달을 여는 entry point 만 제공.

  const unstagedCount = Object.keys(unstagedArtifacts).length;
  const stagedCount = Object.keys(stagedArtifacts).length;

  const openChangesModal = useCallback(() => {
    overlay.modal({
      title: '변경 내역',
      size: 'xl',
      content: <ChangesWorkspaceModal projectId={projectId} />,
    });
  }, [overlay, projectId]);

  // 후보 전체 선택/해제
  const toggleAllCandidates = useCallback(() => {
    if (selectedCandidates.size === candidates.length) {
      setSelectedCandidates(new Set());
    } else {
      setSelectedCandidates(new Set(candidates.map((_, i) => i)));
    }
  }, [candidates, selectedCandidates.size]);

  const toggleCandidate = useCallback((idx: number) => {
    setSelectedCandidates((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  }, []);

  // 선택된 후보 승인
  const handleApproveCandidates = useCallback(async () => {
    if (selectedCandidates.size === 0) return;
    setApproving(true);
    const items: ArtifactRecordCreate[] = Array.from(selectedCandidates).map(
      (idx) => {
        const c = candidates[idx];
        return {
          content: c.content,
          section_id: c.section_id ?? undefined,
          source_document_id: c.source_document_id ?? undefined,
          source_location: c.source_location ?? undefined,
        };
      },
    );

    try {
      await artifactRecordService.approve(projectId, items);
      clearCandidates();
      setSelectedCandidates(new Set());
      await fetchRecords();
    } catch {
      // 글로벌 핸들링
    } finally {
      setApproving(false);
    }
  }, [
    projectId,
    selectedCandidates,
    candidates,
    clearCandidates,
    fetchRecords,
  ]);

  // 후보가 도착하면 전체 선택 — 렌더 중 setState 패턴으로 cascading render 회피
  const [prevCandidates, setPrevCandidates] = useState(candidates);
  if (prevCandidates !== candidates) {
    setPrevCandidates(candidates);
    if (candidates.length > 0) {
      setSelectedCandidates(new Set(candidates.map((_, i) => i)));
    }
  }

  // ── 렌더 ──────────────────────────────────────────────────────────

  const renderContent = () => {
    if (loading) {
      return (
        <div className='flex h-full items-center justify-center'>
          <Spinner size='size-6' className='text-fg-muted' />
        </div>
      );
    }

    if (extracting) {
      return (
        <div className='flex h-full flex-col items-center justify-center p-6 text-center'>
          <Spinner size='size-10' className='text-accent-primary mb-3' />
          <p className='text-fg-primary text-sm font-medium'>
            레코드 추출 중...
          </p>
          <p className='text-fg-muted mt-1 text-xs'>
            지식 문서를 분석하고 있습니다
          </p>
        </div>
      );
    }

    if (extractError) {
      return (
        <div className='flex h-full flex-col items-center justify-center p-6 text-center'>
          <XCircle className='mb-3 size-10 text-red-500' />
          <p className='text-fg-primary text-sm font-medium'>추출 실패</p>
          <p className='text-fg-muted mt-1 text-xs'>{extractError}</p>
        </div>
      );
    }

    if (candidates.length > 0) {
      return renderCandidates();
    }

    if (records.length === 0) {
      return (
        <div className='flex h-full flex-col items-center justify-center p-6 text-center'>
          <FileText className='text-fg-muted mb-3 size-10' />
          <p className='text-fg-secondary text-sm font-medium'>
            레코드가 없습니다
          </p>
          <p className='text-fg-muted mt-1 text-xs'>
            채팅에서 &quot;레코드 추출&quot;을 실행하면 지식 문서에서 자동으로
            추출됩니다.
          </p>
        </div>
      );
    }

    return renderRecordList();
  };

  const renderCandidates = () => (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='border-line-primary flex items-center justify-between border-b px-4 py-2'>
        <div className='flex items-center gap-2'>
          <Database className='text-accent-primary size-4' />
          <span className='text-fg-primary text-xs font-semibold'>
            {candidates.length}개 후보 추출됨
          </span>
        </div>
        <div className='flex items-center gap-2'>
          <Button
            variant='ghost'
            size='sm'
            className='h-7 text-xs'
            onClick={toggleAllCandidates}
          >
            {selectedCandidates.size === candidates.length
              ? '전체 해제'
              : '전체 선택'}
          </Button>
          <Button
            size='sm'
            className='h-7 text-xs'
            onClick={handleApproveCandidates}
            disabled={selectedCandidates.size === 0 || approving}
          >
            {approving ? <Spinner size='size-3' className='mr-1' /> : null}
            {selectedCandidates.size}개 승인
          </Button>
          <Button
            variant='ghost'
            size='sm'
            className='h-7 text-xs text-red-500'
            onClick={clearCandidates}
          >
            취소
          </Button>
        </div>
      </div>

      {/* Candidate list */}
      <ScrollArea className='min-h-0 flex-1'>
        <div className='flex flex-col gap-1.5 p-3 pb-4'>
          {candidates.map((candidate, idx) => {
            const selected = selectedCandidates.has(idx);
            return (
              <button
                key={idx}
                onClick={() => toggleCandidate(idx)}
                className={cn(
                  'group flex items-start gap-3 rounded-lg border px-3.5 py-3 text-left transition-colors',
                  selected
                    ? 'border-fg-primary/30 bg-canvas-primary/60'
                    : 'border-line-primary hover:border-fg-muted/50 hover:bg-canvas-primary/30',
                )}
              >
                <div
                  className={cn(
                    'mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-[4px] border transition-colors',
                    selected
                      ? 'border-fg-primary bg-fg-primary text-canvas-primary'
                      : 'border-fg-muted/50 group-hover:border-fg-muted',
                  )}
                >
                  {selected && <Check className='size-3' strokeWidth={3} />}
                </div>
                <div className='min-w-0 flex-1 space-y-1.5'>
                  {(candidate.section_name ||
                    candidate.confidence_score != null) && (
                    <div className='text-fg-muted flex items-center gap-2 text-[11px]'>
                      {candidate.section_name && (
                        <span className='text-fg-secondary font-medium'>
                          {candidate.section_name}
                        </span>
                      )}
                      {candidate.section_name &&
                        candidate.confidence_score != null && (
                          <span className='opacity-40'>·</span>
                        )}
                      <ConfidenceIndicator score={candidate.confidence_score} />
                    </div>
                  )}
                  <p className='text-fg-primary text-sm leading-relaxed'>
                    {candidate.content}
                  </p>
                  {candidate.source_document_name && (
                    <p className='text-fg-muted truncate text-[11px]'>
                      {candidate.source_document_name}
                      {candidate.source_location && (
                        <span className='opacity-70'>
                          {' '}
                          · {candidate.source_location}
                        </span>
                      )}
                    </p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );

  const renderRecordList = () => (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='border-line-primary flex items-center justify-between border-b px-4 py-2'>
        <span className='text-fg-primary text-xs font-semibold'>
          {records.length}개 레코드
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant='ghost' size='sm' className='h-7 gap-1.5 text-xs'>
              <Filter className='size-3' />
              필터
              {sectionFilters.length > 0 && (
                <Badge className='ml-0.5 h-4 min-w-4 rounded-full px-1 text-[10px]'>
                  {sectionFilters.length}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align='end' className='w-48 text-xs'>
            <DropdownMenuCheckboxItem
              checked={sectionFilters.length === 0}
              onCheckedChange={() => setSectionFilters([])}
              onSelect={(e) => e.preventDefault()}
              className='text-xs'
            >
              전체
            </DropdownMenuCheckboxItem>
            <DropdownMenuSeparator />
            {sections.map(([id, name]) => (
              <DropdownMenuCheckboxItem
                key={id}
                checked={sectionFilters.includes(id)}
                onCheckedChange={(checked) =>
                  setSectionFilters((prev) =>
                    checked ? [...prev, id] : prev.filter((s) => s !== id),
                  )
                }
                onSelect={(e) => e.preventDefault()}
                className='text-xs'
              >
                {name}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Record list */}
      <ScrollArea className='min-h-0 flex-1'>
        <div className='p-3 pb-4'>
          {Object.entries(grouped).map(([sectionName, sectionRecords]) => (
            <div key={sectionName} className='mb-4'>
              <h4 className='text-fg-muted mb-1.5 px-1 text-[10px] font-semibold tracking-wider uppercase'>
                {sectionName}
              </h4>
              <div className='flex flex-col gap-1.5'>
                {sectionRecords.map((record) => {
                  const statusCfg = STATUS_CONFIG[record.status];
                  const StatusIcon = statusCfg.icon;
                  const draft = unstagedArtifacts[record.artifact_id];
                  const displayContent = draft?.content ?? record.content;
                  return (
                    <div
                      key={record.artifact_id}
                      className={cn(
                        'group border-line-primary hover:border-fg-muted/50 hover:bg-canvas-primary/30 space-y-1.5 rounded-lg border px-3.5 py-3 transition-colors',
                        record.status === 'excluded' && 'opacity-50',
                      )}
                    >
                      {/* Top row: ID + confidence + status */}
                      <div className='text-fg-muted flex items-center gap-2 text-[11px]'>
                        <span className='text-fg-secondary font-mono font-medium'>
                          {record.display_id}
                        </span>
                        {draft && (
                          <span className='text-accent-primary inline-flex items-center gap-1 font-medium'>
                            <span className='bg-accent-primary size-1.5 rounded-full' />
                            unstaged
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
                            'ml-auto inline-flex items-center gap-1 [&>svg]:size-3',
                            statusCfg.color,
                          )}
                        >
                          <StatusIcon />
                          {statusCfg.label}
                        </span>
                      </div>

                      {/* Content (드래프트가 있으면 로컬 편집본 우선 표시) */}
                      <p className='text-fg-primary text-sm leading-relaxed'>
                        {displayContent}
                      </p>

                      {/* Source */}
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

                      {/* Actions (visible on hover) */}
                      <div className='mt-1.5 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100'>
                        <Button
                          variant='ghost'
                          size='sm'
                          className='text-fg-secondary h-6 gap-1 px-2 text-[10px]'
                          onClick={() => handleEdit(record)}
                        >
                          <Pencil className='size-3' />
                          편집
                        </Button>
                        {record.status !== 'approved' && (
                          <Button
                            variant='ghost'
                            size='sm'
                            className='h-6 gap-1 px-2 text-[10px] text-green-600'
                            onClick={() =>
                              handleStatusChange(record, 'approved')
                            }
                          >
                            <CheckCircle2 className='size-3' />
                            승인
                          </Button>
                        )}
                        {record.status !== 'excluded' && (
                          <Button
                            variant='ghost'
                            size='sm'
                            className='h-6 gap-1 px-2 text-[10px] text-amber-600'
                            onClick={() =>
                              handleStatusChange(record, 'excluded')
                            }
                          >
                            <XCircle className='size-3' />
                            제외
                          </Button>
                        )}
                        {record.status === 'excluded' && (
                          <Button
                            variant='ghost'
                            size='sm'
                            className='h-6 gap-1 px-2 text-[10px]'
                            onClick={() => handleStatusChange(record, 'draft')}
                          >
                            복원
                          </Button>
                        )}
                        <Button
                          variant='ghost'
                          size='icon'
                          className='text-fg-muted hover:text-destructive ml-auto size-6'
                          onClick={() => handleDelete(record.artifact_id)}
                        >
                          <Trash2 className='size-3' />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );

  return (
    <div className='flex h-full flex-row'>
      <div className='flex min-w-0 flex-1 flex-col'>
        <WorkspaceStatusBar
          unstagedCount={unstagedCount}
          stagedCount={stagedCount}
          openPRsCount={openPRs.length}
          onOpenTray={openChangesModal}
        />
        {renderContent()}
      </div>
    </div>
  );
}
