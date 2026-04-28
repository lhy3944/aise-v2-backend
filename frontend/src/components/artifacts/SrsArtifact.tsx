'use client';

import {
  Download,
  FileText,
  Link2,
  Pencil,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  SrsSectionEditor,
  SrsSectionEditorActions,
  type SrsSectionEditorValues,
} from '@/components/artifacts/workspace/editor/SrsSectionEditor';
import { StaleBadge } from '@/components/artifacts/workspace/StaleBadge';
import { MessageResponse } from '@/components/ui/ai-elements/message';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import { useImpact } from '@/hooks/useImpact';
import { useOverlay } from '@/hooks/useOverlay';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/utils';
import { srsService } from '@/services/srs-service';
import { useArtifactActionStore } from '@/stores/artifact-action-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { useProjectStore } from '@/stores/project-store';
import { EMPTY_BUCKET, useStagingStore } from '@/stores/staging-store';
import type { SrsDocument, SrsSection } from '@/types/project';

const STATUS_LABEL: Record<string, { label: string; tone: string }> = {
  completed: { label: '완료', tone: 'bg-green-600 text-white' },
  generating: { label: '생성중', tone: 'bg-amber-600 text-white' },
  failed: { label: '실패', tone: 'bg-red-600 text-white' },
};

function StatusChip({ status }: { status: string }) {
  const cfg = STATUS_LABEL[status] ?? {
    label: status,
    tone: 'bg-canvas-primary text-fg-muted',
  };
  return (
    <span
      className={cn(
        'rounded px-2 py-0.5 text-[10px] font-medium whitespace-nowrap',
        cfg.tone,
      )}
    >
      {cfg.label}
    </span>
  );
}

function toMarkdown(doc: SrsDocument): string {
  // 섹션 content 자체에 이미 헤딩(#/##) 이 포함되어 있으므로 '## title' 미추가.
  const parts: string[] = [];
  for (const section of doc.sections) {
    if (section.content) parts.push(section.content.trim());
  }
  return parts.join('\n\n') + '\n';
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function formatCreatedAt(value: string) {
  // 간결한 ISO-like 포맷: 2026-04-27 16:30
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return value;
  }
}

export function SrsArtifact() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const projectId = currentProject?.project_id;

  const [documents, setDocuments] = useState<SrsDocument[]>([]);
  const [selectedSrsId, setSelectedSrsId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // 진행 중 액션 상태 — store 로 끌어올려 탭 unmount/remount 사이에서도 유지.
  const generating = useArtifactActionStore((s) => s.generating.srs);
  const setGenerating = useArtifactActionStore((s) => s.setGenerating);
  // 출처 보기 → Records 탭 이동 + 다른 탭에서 넘어온 pendingFocus 처리.
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const pendingFocus = useArtifactStore((s) => s.pendingFocus);
  const setPendingFocus = useArtifactStore((s) => s.setPendingFocus);

  const overlay = useOverlay();

  // PR 머지/거절/생성 시 list 갱신 트리거
  const refreshNonce = useArtifactRefreshStore((s) => s.nonce.srs);

  // Phase F: stale 판정 — record/SRS/Design/TC 어느 쪽이 머지되어도 자동 재조회
  const { staleByArtifactId } = useImpact(projectId);

  // SRS Artifact 단위 unstaged/staged 드래프트 — content 는 sections 전체 snapshot
  const unstagedArtifacts = useStagingStore(
    (s) =>
      (projectId && s.byProject[projectId]?.unstaged) || EMPTY_BUCKET.unstaged,
  );
  const stagedArtifacts = useStagingStore(
    (s) => (projectId && s.byProject[projectId]?.staged) || EMPTY_BUCKET.staged,
  );
  const _setDraft = useStagingStore((s) => s.setDraft);
  const setArtifactDraft = useCallback(
    (draft: Parameters<typeof _setDraft>[1]) => {
      if (!projectId) return;
      _setDraft(projectId, draft);
    },
    [_setDraft, projectId],
  );

  const selectedDoc = useMemo(
    () => documents.find((d) => d.srs_id === selectedSrsId) ?? null,
    [documents, selectedSrsId],
  );

  const fetchList = useCallback(
    async (preferId?: string) => {
      if (!projectId) return;
      try {
        const res = await srsService.list(projectId);
        const sorted = [...res.documents].sort((a, b) => b.version - a.version);
        setDocuments(sorted);
        setSelectedSrsId((prev) => {
          if (preferId && sorted.some((d) => d.srs_id === preferId)) {
            return preferId;
          }
          if (prev && sorted.some((d) => d.srs_id === prev)) return prev;
          return sorted[0]?.srs_id ?? null;
        });
      } finally {
        setLoading(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    void fetchList();
  }, [projectId, fetchList, refreshNonce]);

  // 다른 탭의 "출처 보기" 로 넘어온 pendingFocus 처리 — 해당 SRS version 자동 선택.
  // documents 가 로드된 후에만 적용 가능하므로 documents 의존성에 포함.
  useEffect(() => {
    if (
      pendingFocus?.kind === 'srs' &&
      pendingFocus.versionId &&
      documents.some((d) => d.srs_id === pendingFocus.versionId)
    ) {
      setSelectedSrsId(pendingFocus.versionId);
      setPendingFocus(null);
    }
  }, [pendingFocus, documents, setPendingFocus]);

  const handleGenerate = useCallback(async () => {
    if (!projectId) return;
    setGenerating('srs', true);
    setErrorMessage(null);
    try {
      const doc = await srsService.generate(projectId);
      await fetchList(doc.srs_id);
    } catch (err) {
      if (err instanceof ApiError) setErrorMessage(err.message);
    } finally {
      setGenerating('srs', false);
    }
  }, [projectId, fetchList, setGenerating]);

  const handleEditSection = useCallback(
    (section: SrsSection) => {
      if (!projectId || !selectedDoc || !section.section_id) return;

      const sectionId = section.section_id;
      const artifactId = selectedDoc.artifact_id;

      // 기존 unstaged 드래프트가 있으면 그 sections 를 base 로, 없으면 server 원본을 base.
      const existing = unstagedArtifacts[artifactId];
      const baseSections =
        (existing?.content?.sections as SrsSection[] | undefined) ??
        selectedDoc.sections;

      const handleSubmit = (values: SrsSectionEditorValues) => {
        // 편집한 섹션만 새 content 로 교체, 나머지 섹션은 그대로 보존.
        const nextSections = baseSections.map((s) =>
          s.section_id === sectionId ? { ...s, content: values.content } : s,
        );
        // SRS Artifact 의 working copy 전체 snapshot 을 staging-store 에 저장.
        // 백엔드 PATCH /artifacts/{id} 가 이 객체를 그대로 받는다.
        setArtifactDraft({
          artifactId,
          artifactKind: 'srs',
          content: {
            sections: nextSections,
            based_on_records: selectedDoc.based_on_records ?? null,
            based_on_documents: selectedDoc.based_on_documents ?? null,
            status: selectedDoc.status,
            error_message: selectedDoc.error_message,
          },
          originalContent: {
            sections: selectedDoc.sections,
            based_on_records: selectedDoc.based_on_records ?? null,
            based_on_documents: selectedDoc.based_on_documents ?? null,
            status: selectedDoc.status,
            error_message: selectedDoc.error_message,
          },
          editedAt: new Date().toISOString(),
          displayLabel: `SRS v${selectedDoc.version}`,
        });
        overlay.closeModal();
      };

      overlay.modal({
        title: `섹션 편집 — ${section.title}`,
        description:
          '저장해도 서버에는 아직 반영되지 않습니다 — Unstaged 드래프트로 누적됩니다.',
        size: 'lg',
        content: <SrsSectionEditor section={section} onSubmit={handleSubmit} />,
        footer: (
          <SrsSectionEditorActions onCancel={() => overlay.closeModal()} />
        ),
      });
    },
    [projectId, selectedDoc, overlay, unstagedArtifacts, setArtifactDraft],
  );

  if (!projectId) return null;

  if (loading) {
    return (
      <div className='flex h-full items-center justify-center'>
        <Spinner size='size-6' className='text-fg-muted' />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className='flex h-full flex-col items-center justify-center gap-3 p-6 text-center'>
        <FileText className='text-fg-muted size-10' />
        <div>
          <p className='text-fg-secondary text-sm font-medium'>SRS 문서 없음</p>
          <p className='text-fg-muted mt-1 text-xs'>
            승인된 레코드를 기반으로 SRS 초안을 생성합니다.
          </p>
        </div>
        <Button
          size='sm'
          variant={'default'}
          onClick={handleGenerate}
          disabled={generating}
          className='gap-2 px-5!'
        >
          {generating ? (
            <Spinner size='size-3.5' />
          ) : (
            <Sparkles className='size-3.5' />
          )}
          <span className='text-xs'>SRS 생성</span>
        </Button>
        {errorMessage && (
          <p className='text-destructive text-xs'>{errorMessage}</p>
        )}
      </div>
    );
  }

  const handleDownloadMarkdown = () => {
    if (!selectedDoc) return;
    const md = toMarkdown(selectedDoc);
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    downloadBlob(blob, `SRS-v${selectedDoc.version}.md`);
  };

  return (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='border-line-primary flex flex-col gap-2 border-b px-4 py-2 md:flex-row md:items-center md:justify-between'>
        <div className='flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1'>
          <Select
            value={selectedSrsId ?? undefined}
            onValueChange={(v) => setSelectedSrsId(v)}
          >
            <SelectTrigger
              size='sm'
              className='h-7 w-full gap-2 text-xs md:w-auto md:min-w-[220px]'
            >
              <SelectValue placeholder='버전 선택'>
                {selectedDoc && (
                  <span className='flex items-center gap-2'>
                    <StatusChip status={selectedDoc.status} />
                    <span className='text-fg-primary font-medium'>
                      v{selectedDoc.version}
                    </span>
                    <span className='text-fg-muted whitespace-nowrap'>
                      {formatCreatedAt(selectedDoc.created_at)}
                    </span>
                  </span>
                )}
              </SelectValue>
            </SelectTrigger>
            {selectedDoc && staleByArtifactId[selectedDoc.artifact_id] && (
              <StaleBadge impact={staleByArtifactId[selectedDoc.artifact_id]} />
            )}
            <SelectContent>
              {documents.map((doc) => {
                return (
                  <SelectItem
                    key={doc.srs_id}
                    value={doc.srs_id}
                    className='text-xs'
                  >
                    <span className='flex w-full items-center gap-2'>
                      <StatusChip status={doc.status} />
                      <span className='text-fg-primary font-medium'>
                        v{doc.version}
                      </span>
                      <span className='text-fg-muted whitespace-nowrap'>
                        {formatCreatedAt(doc.created_at)}
                      </span>
                    </span>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>
        <div className='flex items-center justify-end gap-1.5'>
          {selectedDoc?.source_artifact_versions?.record &&
            selectedDoc.source_artifact_versions.record.length > 0 && (
              <Button
                variant='ghost'
                size='sm'
                className='h-7 gap-1.5 text-xs'
                onClick={() => setActiveTab('records')}
              >
                <Link2 className='size-3.5' />
                출처 보기
              </Button>
            )}
          <Button
            variant='ghost'
            size='sm'
            className='h-7 gap-1.5 text-xs'
            disabled={!selectedDoc}
            onClick={handleDownloadMarkdown}
          >
            <Download className='size-3.5' />
            다운로드
          </Button>
          <Button
            variant='ghost'
            size='sm'
            className='h-7 gap-1.5 text-xs'
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? (
              <Spinner size='size-3.5' />
            ) : (
              <RefreshCw className='size-3.5' />
            )}
            재생성
          </Button>
        </div>
      </div>

      {/* Body */}
      {selectedDoc && selectedDoc.status === 'failed' && (
        <div className='border-line-primary border-b px-4 py-2 text-xs text-red-500'>
          생성 실패: {selectedDoc.error_message ?? '알 수 없는 오류'}
        </div>
      )}

      <ScrollArea className='min-h-0 flex-1'>
        <div className='flex flex-col gap-4 p-4 pb-6'>
          {(() => {
            if (!selectedDoc) return null;
            // 드래프트가 있으면 그 sections 를 우선 표시 (Unstaged > Staged > Server).
            const unstagedDraft = unstagedArtifacts[selectedDoc.artifact_id];
            const stagedDraft = stagedArtifacts[selectedDoc.artifact_id];
            const draftSections =
              (unstagedDraft?.content?.sections as SrsSection[] | undefined) ??
              (stagedDraft?.content?.sections as SrsSection[] | undefined);
            const displaySections = draftSections ?? selectedDoc.sections;
            const draftTone = unstagedDraft
              ? 'amber'
              : stagedDraft
                ? 'blue'
                : null;
            return (
              <>
                {draftTone && (
                  <div
                    className={cn(
                      'rounded-md border px-3 py-2 text-xs',
                      draftTone === 'amber'
                        ? 'border-amber-500/40 bg-amber-500/5 text-amber-700 dark:text-amber-400'
                        : 'border-blue-500/40 bg-blue-500/5 text-blue-700 dark:text-blue-400',
                    )}
                  >
                    {draftTone === 'amber'
                      ? '편집 중인 드래프트가 있습니다 (서버 미반영) — 변경 내역 모달에서 Stage / PR 생성하세요.'
                      : 'Staged 변경이 PR 머지를 대기 중입니다.'}
                  </div>
                )}
                {displaySections.map((section, idx) => (
                  <section
                    key={section.section_id ?? `idx-${idx}`}
                    className='border-line-primary group rounded-lg border'
                  >
                    <header className='mb-2 flex items-center justify-between gap-2 bg-canvas-surface rounded-t-lg px-4 py-3'>
                      <h3 className='text-fg-primary text-sm font-semibold'>
                        {section.title}
                      </h3>
                      {section.section_id && (
                        <Button
                          variant='ghost'
                          size='sm'
                          className='text-fg-secondary h-6 gap-1 px-2 text-[10px] opacity-0 transition-opacity group-hover:opacity-100'
                          onClick={() => handleEditSection(section)}
                        >
                          <Pencil className='size-3' />
                          편집
                        </Button>
                      )}
                    </header>
                    {section.content ? (
                      <MessageResponse className='text-sm px-4'>
                        {section.content}
                      </MessageResponse>
                    ) : (
                      <p className='text-fg-muted text-xs italic'>내용 없음</p>
                    )}
                  </section>
                ))}
                {displaySections.length === 0 && (
                  <p className='text-fg-muted text-center text-xs'>
                    섹션이 없습니다.
                  </p>
                )}
              </>
            );
          })()}
        </div>
      </ScrollArea>
    </div>
  );
}
