'use client';

import { ArtifactEmptyGuide } from '@/components/artifacts/ArtifactEmptyGuide';
import { ManualRecordModal } from '@/components/artifacts/ManualRecordModal';
import { CandidateCard } from '@/components/artifacts/records/CandidateCard';
import { RecordCard } from '@/components/artifacts/records/RecordCard';
import { ChangesWorkspaceModal } from '@/components/artifacts/workspace/ChangesWorkspaceModal';
import {
  ArtifactRecordEditor,
  ArtifactRecordEditorActions,
  type ArtifactRecordEditorValues,
} from '@/components/artifacts/workspace/editor/ArtifactRecordEditor';
import { RecordVersionsModal } from '@/components/artifacts/workspace/RecordVersionsModal';
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
import { artifactRecordService } from '@/services/artifact-record-service';
import { artifactService } from '@/services/artifact-service';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { usePrStore } from '@/stores/pr-store';
import { EMPTY_BUCKET, useStagingStore } from '@/stores/staging-store';
import type {
  ArtifactRecord,
  ArtifactRecordCreate,
  ArtifactRecordStatus,
} from '@/types/project';
import {
  Database,
  Filter,
  MessageSquareText,
  PenLine,
  Plus,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { memo, useCallback, useEffect, useState } from 'react';

interface ArtifactRecordsPanelProps {
  projectId: string;
}

const EMPTY_RECORD_GUIDES = [
  {
    icon: Sparkles,
    title: '문서에서 추출',
    description: '업로드한 지식 문서를 분석해 후보 레코드를 만듭니다.',
  },
  {
    icon: MessageSquareText,
    title: '대화에서 정리',
    description: '채팅 중 확정한 요구사항을 레코드 후보로 전환합니다.',
  },
  {
    icon: PenLine,
    title: '직접 등록',
    description: '이미 확정된 항목은 폼으로 바로 추가합니다.',
  },
];

export const ArtifactRecordsPanel = memo(function ArtifactRecordsPanel({
  projectId,
}: ArtifactRecordsPanelProps) {
  const [records, setRecords] = useState<ArtifactRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [sectionFilters, setSectionFilters] = useState<string[]>([]);
  const [manualOpen, setManualOpen] = useState(false);

  const extracting = useArtifactRecordStore((s) => s.extracting);
  const candidates = useArtifactRecordStore((s) => s.candidates);
  const extractError = useArtifactRecordStore((s) => s.extractError);
  const clearCandidates = useArtifactRecordStore((s) => s.clearCandidates);
  const refreshNonce = useArtifactRecordStore((s) => s.refreshNonce);
  const bumpRefresh = useArtifactRecordStore((s) => s.bumpRefresh);
  const [selectedCandidates, setSelectedCandidates] = useState<Set<number>>(
    new Set(),
  );
  const [approving, setApproving] = useState(false);

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
    let cancelled = false;

    artifactRecordService
      .list(projectId)
      .then((res) => {
        if (!cancelled) setRecords(res.records);
      })
      .catch(() => {
        // 글로벌 핸들링
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, refreshNonce]);

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

  const sections = Array.from(
    new Map(
      records
        .filter((r) => r.section_id && r.section_name)
        .map((r) => [r.section_id!, r.section_name!]),
    ),
  );

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
        useArtifactRefreshStore.getState().bump('record');
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
        useArtifactRefreshStore.getState().bump('record');
      } catch {
        // 글로벌 핸들링
      }
    },
    [projectId, discardArtifactDraft],
  );

  const handleShowVersions = useCallback(
    (record: ArtifactRecord) => {
      overlay.modal({
        title: `버전 히스토리 ${record.display_id}`,
        description: '이 레코드의 버전과 변경 내역 입니다.',
        size: '2xl',
        content: (
          <RecordVersionsModal
            projectId={projectId}
            artifactId={record.artifact_id}
            displayLabel={record.display_id}
          />
        ),
      });
    },
    [overlay, projectId],
  );

  const handleEdit = useCallback(
    (record: ArtifactRecord) => {
      const existing = unstagedArtifacts[record.artifact_id];
      const draftBody =
        typeof existing?.content?.text === 'string'
          ? (existing.content.text as string)
          : undefined;

      const handleSubmit = (values: ArtifactRecordEditorValues) => {
        if (values.content.trim() === record.content.trim()) {
          discardArtifactDraft(record.artifact_id);
        } else {
          const baseSnapshot = {
            text: record.content,
            section_id: record.section_id,
            source_document_id: record.source_document_id,
            source_location: record.source_location,
            confidence_score: record.confidence_score,
            is_auto_extracted: record.is_auto_extracted,
            order_index: record.order_index,
            metadata: { status: record.status },
          };
          setArtifactDraft({
            artifactId: record.artifact_id,
            artifactKind: 'record',
            content: { ...baseSnapshot, text: values.content },
            originalContent: baseSnapshot,
            editedAt: new Date().toISOString(),
            displayLabel: record.display_id,
          });
        }
        overlay.closeModal();
      };

      overlay.modal({
        title: '레코드 편집',
        description:
          '저장해도 서버에는 아직 반영되지 않습니다 (Unstaged 드래프트로 누적됩니다)',
        size: 'md',
        content: (
          <ArtifactRecordEditor
            record={record}
            draftContent={draftBody}
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

  const unstagedCount = Object.keys(unstagedArtifacts).length;
  const stagedCount = Object.keys(stagedArtifacts).length;

  const openChangesModal = useCallback(() => {
    overlay.modal({
      title: '변경 내역',
      size: 'xl',
      content: <ChangesWorkspaceModal projectId={projectId} />,
    });
  }, [overlay, projectId]);

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
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  }, []);

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
          confidence_score: c.confidence_score ?? undefined,
        };
      },
    );

    try {
      await artifactRecordService.approve(projectId, items);
      clearCandidates();
      setSelectedCandidates(new Set());
      await fetchRecords();
      useArtifactRefreshStore.getState().bump('record');
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

  const [prevCandidates, setPrevCandidates] = useState(candidates);
  if (prevCandidates !== candidates) {
    setPrevCandidates(candidates);
    if (candidates.length > 0) {
      setSelectedCandidates(new Set(candidates.map((_, i) => i)));
    }
  }

  return (
    <div className='flex h-full flex-row'>
      <div className='flex min-w-0 flex-1 flex-col'>
        <WorkspaceStatusBar
          unstagedCount={unstagedCount}
          stagedCount={stagedCount}
          openPRsCount={openPRs.length}
          onOpenTray={openChangesModal}
        />

        {loading ? (
          <div className='flex h-full items-center justify-center'>
            <Spinner size='size-6' className='text-fg-muted' />
          </div>
        ) : extracting ? (
          <div className='flex h-full flex-col items-center justify-center p-6 text-center'>
            <Spinner size='size-10' className='text-accent-primary mb-3' />
            <p className='text-fg-primary text-sm font-medium'>
              레코드 추출 중...
            </p>
            <p className='text-fg-muted mt-1 text-xs'>
              지식 문서를 분석하고 있습니다
            </p>
          </div>
        ) : extractError ? (
          <div className='flex h-full flex-col items-center justify-center p-6 text-center'>
            <XCircle className='mb-3 size-10 text-red-500' />
            <p className='text-fg-primary text-sm font-medium'>추출 실패</p>
            <p className='text-fg-muted mt-1 text-xs'>{extractError}</p>
          </div>
        ) : candidates.length > 0 ? (
          <div className='flex h-full flex-col'>
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
                  {approving ? (
                    <Spinner size='size-3' className='mr-1' />
                  ) : null}
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
            <ScrollArea className='min-h-0 flex-1'>
              <div className='flex flex-col gap-1.5 p-3 pb-4'>
                {candidates.map((candidate, idx) => (
                  <CandidateCard
                    key={idx}
                    candidate={candidate}
                    idx={idx}
                    selected={selectedCandidates.has(idx)}
                    onToggle={toggleCandidate}
                  />
                ))}
              </div>
            </ScrollArea>
          </div>
        ) : records.length === 0 ? (
          <ArtifactEmptyGuide
            icon={Database}
            title='레코드가 존재하지 않습니다.'
            description='요구사항 문장으로 산출물 생성을 준비합니다.'
            guides={EMPTY_RECORD_GUIDES}
            action={
              <Button
                size='sm'
                className='h-8 gap-1.5 px-3 text-xs'
                onClick={() => setManualOpen(true)}
              >
                <Plus className='size-4' />
                직접 추가
              </Button>
            }
          />
        ) : (
          <div className='flex h-full flex-col'>
            <div className='border-line-primary flex items-center justify-between border-b px-4 py-2'>
              <span className='text-fg-primary text-xs font-semibold'>
                {records.length}개 레코드
              </span>
              <div className='flex items-center gap-1'>
                <Button
                  variant='ghost'
                  size='sm'
                  className='h-7 gap-1 text-xs'
                  onClick={() => setManualOpen(true)}
                  title='레코드 직접 추가'
                >
                  <Plus className='size-3' />
                  추가
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant='ghost'
                      size='sm'
                      className='h-7 gap-1.5 text-xs'
                    >
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
                            checked
                              ? [...prev, id]
                              : prev.filter((s) => s !== id),
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
            </div>
            <ScrollArea className='min-h-0 flex-1'>
              <div className='p-3 pb-4'>
                {Object.entries(grouped).map(
                  ([sectionName, sectionRecords]) => (
                    <div key={sectionName} className='mb-4'>
                      <h4 className='text-fg-muted mb-1.5 px-1 text-[10px] font-semibold tracking-wider uppercase'>
                        {sectionName}
                      </h4>
                      <div className='flex flex-col gap-1.5'>
                        {sectionRecords.map((record) => {
                          const draft = unstagedArtifacts[record.artifact_id];
                          const draftText =
                            draft && typeof draft.content?.text === 'string'
                              ? (draft.content.text as string)
                              : null;
                          return (
                            <RecordCard
                              key={record.artifact_id}
                              record={record}
                              draftText={draftText}
                              onEdit={handleEdit}
                              onShowVersions={handleShowVersions}
                              onStatusChange={handleStatusChange}
                              onDelete={handleDelete}
                            />
                          );
                        })}
                      </div>
                    </div>
                  ),
                )}
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
      <ManualRecordModal
        open={manualOpen}
        onOpenChange={setManualOpen}
        projectId={projectId}
        onCreated={() => {
          bumpRefresh();
        }}
        onError={(msg) => {
          overlay.alert({
            type: 'error',
            title: '레코드 추가 실패',
            description: msg,
          });
        }}
      />
    </div>
  );
});
