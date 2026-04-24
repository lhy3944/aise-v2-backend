'use client';

import {
  Download,
  FileText,
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
import { MessageResponse } from '@/components/ui/ai-elements/message';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import { useOverlay } from '@/hooks/useOverlay';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/utils';
import { srsService } from '@/services/srs-service';
import { useProjectStore } from '@/stores/project-store';
import type { SrsDocument, SrsSection } from '@/types/project';

const STATUS_LABEL: Record<string, { label: string; tone: string }> = {
  completed: { label: '완료', tone: 'bg-green-500/10 text-green-600' },
  generating: { label: '생성중', tone: 'bg-amber-500/10 text-amber-600' },
  failed: { label: '실패', tone: 'bg-red-500/10 text-red-600' },
};

function StatusChip({ status }: { status: string }) {
  const cfg = STATUS_LABEL[status] ?? {
    label: status,
    tone: 'bg-canvas-primary text-fg-muted',
  };
  return (
    <span
      className={cn(
        'rounded px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap',
        cfg.tone,
      )}
    >
      {cfg.label}
    </span>
  );
}

function toMarkdown(doc: SrsDocument): string {
  const lines: string[] = [
    `# SRS v${doc.version}`,
    '',
    `생성일: ${formatCreatedAt(doc.created_at)}`,
    `상태: ${STATUS_LABEL[doc.status]?.label ?? doc.status}`,
    '',
  ];
  for (const section of doc.sections) {
    lines.push(`## ${section.title}`, '');
    if (section.content) lines.push(section.content, '');
  }
  return lines.join('\n');
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
  try {
    const d = new Date(value);
    return d.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
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
  const [generating, setGenerating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const overlay = useOverlay();

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
  }, [projectId, fetchList]);

  const handleGenerate = useCallback(async () => {
    if (!projectId) return;
    setGenerating(true);
    setErrorMessage(null);
    try {
      const doc = await srsService.generate(projectId);
      await fetchList(doc.srs_id);
    } catch (err) {
      if (err instanceof ApiError) setErrorMessage(err.message);
    } finally {
      setGenerating(false);
    }
  }, [projectId, fetchList]);

  const handleEditSection = useCallback(
    (section: SrsSection) => {
      if (!projectId || !selectedDoc || !section.section_id) return;

      const srsId = selectedDoc.srs_id;
      const sectionId = section.section_id;

      const handleSubmit = async (values: SrsSectionEditorValues) => {
        try {
          const updated = await srsService.updateSection(
            projectId,
            srsId,
            sectionId,
            values.content,
          );
          setDocuments((prev) =>
            prev.map((d) => (d.srs_id === updated.srs_id ? updated : d)),
          );
          overlay.closeModal();
        } catch {
          // 글로벌 핸들러가 토스트 노출
        }
      };

      overlay.modal({
        title: `섹션 편집 — ${section.title}`,
        size: 'lg',
        content: <SrsSectionEditor section={section} onSubmit={handleSubmit} />,
        footer: (
          <SrsSectionEditorActions onCancel={() => overlay.closeModal()} />
        ),
      });
    },
    [projectId, selectedDoc, overlay],
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
          onClick={handleGenerate}
          disabled={generating}
          className='gap-1.5'
        >
          {generating ? (
            <Spinner size='size-3' />
          ) : (
            <Sparkles className='size-3.5' />
          )}
          SRS 생성
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

  const handleDownloadPdf = () => {
    // 브라우저 인쇄 대화상자로 우회 — "PDF로 저장" 옵션 선택 시 결과물.
    // 장기적으로는 백엔드 export 엔드포인트로 교체 예정.
    window.print();
  };

  return (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='border-line-primary flex items-center justify-between gap-2 border-b px-4 py-2'>
        <div className='flex min-w-0 items-center gap-2'>
          <Select
            value={selectedSrsId ?? undefined}
            onValueChange={(v) => setSelectedSrsId(v)}
          >
            <SelectTrigger
              size='sm'
              className='h-7 w-auto min-w-[220px] gap-2 text-xs'
            >
              <SelectValue placeholder='버전 선택'>
                {selectedDoc && (
                  <span className='flex items-center gap-2'>
                    <span className='text-fg-primary font-medium'>
                      v{selectedDoc.version}
                    </span>
                    <span className='text-fg-muted whitespace-nowrap'>
                      {formatCreatedAt(selectedDoc.created_at)}
                    </span>
                    <StatusChip status={selectedDoc.status} />
                  </span>
                )}
              </SelectValue>
            </SelectTrigger>
            <SelectContent className='min-w-[260px]'>
              {documents.map((doc) => (
                <SelectItem
                  key={doc.srs_id}
                  value={doc.srs_id}
                  className='text-xs'
                >
                  <span className='flex w-full items-center gap-2'>
                    <span className='text-fg-primary font-medium'>
                      v{doc.version}
                    </span>
                    <span className='text-fg-muted whitespace-nowrap'>
                      {formatCreatedAt(doc.created_at)}
                    </span>
                    <span className='ml-auto'>
                      <StatusChip status={doc.status} />
                    </span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className='flex items-center gap-1.5'>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant='outline'
                size='sm'
                className='h-7 gap-1.5 text-xs'
                disabled={!selectedDoc}
              >
                <Download className='size-3' />
                다운로드
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align='end' className='w-44 text-xs'>
              <DropdownMenuItem
                className='text-xs'
                onClick={handleDownloadMarkdown}
              >
                Markdown (.md)
              </DropdownMenuItem>
              <DropdownMenuItem className='text-xs' onClick={handleDownloadPdf}>
                PDF — 인쇄로 저장
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            variant='outline'
            size='sm'
            className='h-7 gap-1.5 text-xs'
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? (
              <Spinner size='size-3' />
            ) : (
              <RefreshCw className='size-3' />
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
          {selectedDoc?.sections.map((section, idx) => (
            <section
              key={section.section_id ?? `idx-${idx}`}
              className='border-line-primary bg-canvas-surface group rounded-lg border px-4 py-3'
            >
              <header className='mb-2 flex items-center justify-between gap-2'>
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
                <MessageResponse className='text-sm'>
                  {section.content}
                </MessageResponse>
              ) : (
                <p className='text-fg-muted text-xs italic'>내용 없음</p>
              )}
            </section>
          ))}
          {selectedDoc && selectedDoc.sections.length === 0 && (
            <p className='text-fg-muted text-center text-xs'>
              섹션이 없습니다.
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
