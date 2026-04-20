'use client';

import { KnowledgePreviewModal } from '@/components/projects/KnowledgePreviewModal';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '@/components/ui/hover-card';
import { Switch } from '@/components/ui/switch';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useOverlay } from '@/hooks/useOverlay';
import { cn } from '@/lib/utils';
import { knowledgeService } from '@/services/knowledge-service';
import { Spinner } from '@/components/ui/spinner';
import { useProjectStore } from '@/stores/project-store';
import { useReadinessStore } from '@/stores/readiness-store';
import type {
  KnowledgeDocument,
  KnowledgeDocumentFileType,
  KnowledgeDocumentStatus,
} from '@/types/project';
import {
  Ban,
  Check,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
  Text,
  Trash2,
  Upload,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useDeferredLoading } from '@/hooks/useDeferredLoading';
import { ListSkeleton } from '../shared/ListSkeleton';
import { Textarea } from '../ui/textarea';

type KnowledgeInputMode = 'file' | 'text';

const INPUT_MODES: {
  value: KnowledgeInputMode;
  label: string;
  icon: typeof Upload;
}[] = [
  { value: 'file', label: '첨부 파일', icon: Upload },
  { value: 'text', label: '텍스트 입력', icon: Text },
];

interface ProjectKnowledgeTabProps {
  projectId: string;
}

const FILE_TYPE_ICON: Record<KnowledgeDocumentFileType, typeof FileText> = {
  pdf: FileText,
  md: FileText,
  txt: FileText,
};

const FILE_TYPE_COLOR: Record<KnowledgeDocumentFileType, string> = {
  pdf: 'bg-red-500/10 text-red-600 dark:text-red-400',
  md: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  txt: 'bg-gray-500/10 text-gray-600 dark:text-gray-400',
};

const STATUS_CONFIG: Record<
  KnowledgeDocumentStatus,
  { icon: typeof FileText; label: string; color: string }
> = {
  pending: { icon: Clock, label: '대기', color: 'text-gray-500' },
  processing: {
    icon: Loader2,
    label: '분석중',
    color: 'text-amber-600 dark:text-amber-400',
  },
  completed: {
    icon: Check,
    label: '완료',
    color: 'text-green-600 dark:text-green-400',
  },
  failed: { icon: Ban, label: '실패', color: 'text-red-600 dark:text-red-400' },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ProjectKnowledgeTab({ projectId }: ProjectKnowledgeTabProps) {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const showSkeleton = useDeferredLoading(loading);
  const [dragging, setDragging] = useState(false);
  const [previewTarget, setPreviewTarget] = useState<KnowledgeDocument | null>(
    null,
  );
  const [inputMode, setInputMode] = useState<KnowledgeInputMode>('file');
  const [textContent, setTextContent] = useState('');
  const [textFormat, setTextFormat] = useState<'txt' | 'md'>('txt');
  const [textSubmitting, setTextSubmitting] = useState(false);
  const projectName = useProjectStore(
    (s) => s.currentProject?.name ?? 'project',
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const overlay = useOverlay();
  const invalidateReadiness = useReadinessStore((s) => s.invalidate);

  // 문서 목록 조회
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await knowledgeService.list(projectId);
      setDocuments(res.documents);
    } catch {
      // api.ts의 글로벌 에러 핸들링이 토스트를 표시
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // processing 상태 문서가 있으면 5초마다 폴링
  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.status === 'processing' || d.status === 'pending',
    );
    if (!hasProcessing) return;

    const interval = setInterval(fetchDocuments, 5000);
    return () => clearInterval(interval);
  }, [documents, fetchDocuments]);

  // 파일 업로드 처리
  const handleUploadFiles = useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;
      setUploading(true);

      for (const file of files) {
        try {
          await knowledgeService.upload(projectId, file);
        } catch (err: unknown) {
          const error = err as Error & { status?: number };
          if (error.status === 409) {
            overlay.confirm({
              title: '중복 파일',
              description: `"${file.name}" 파일이 이미 존재합니다. 덮어쓰시겠습니까?`,
              confirmLabel: '덮어쓰기',
              variant: 'destructive',
              onConfirm: async () => {
                try {
                  await knowledgeService.upload(projectId, file, true);
                  await fetchDocuments();
                } catch {
                  // 글로벌 핸들링
                }
              },
            });
            continue;
          }
        }
      }

      await fetchDocuments();
      invalidateReadiness();
      setUploading(false);
    },
    [projectId, fetchDocuments, overlay, invalidateReadiness],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const files = Array.from(e.dataTransfer.files);
      handleUploadFiles(files);
    },
    [handleUploadFiles],
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files ?? []);
      handleUploadFiles(files);
      e.target.value = '';
    },
    [handleUploadFiles],
  );

  // 토글
  const handleToggle = useCallback(
    async (doc: KnowledgeDocument) => {
      try {
        const updated = await knowledgeService.toggle(
          projectId,
          doc.document_id,
          !doc.is_active,
        );
        setDocuments((prev) =>
          prev.map((d) =>
            d.document_id === updated.document_id ? updated : d,
          ),
        );
        invalidateReadiness();
      } catch {
        // 글로벌 핸들링
      }
    },
    [projectId, invalidateReadiness],
  );

  // 재처리
  const handleReprocess = useCallback(
    async (e: React.MouseEvent, doc: KnowledgeDocument) => {
      e.stopPropagation();
      try {
        const updated = await knowledgeService.reprocess(
          projectId,
          doc.document_id,
        );
        setDocuments((prev) =>
          prev.map((d) =>
            d.document_id === updated.document_id ? updated : d,
          ),
        );
      } catch {
        // 글로벌 핸들링
      }
    },
    [projectId],
  );

  // 삭제
  const handleDelete = useCallback(
    (e: React.MouseEvent, doc: KnowledgeDocument) => {
      e.stopPropagation();
      overlay.confirm({
        title: '문서 삭제',
        description: `"${doc.name}" 문서를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`,
        confirmLabel: '삭제',
        variant: 'destructive',
        onConfirm: async () => {
          try {
            await knowledgeService.delete(projectId, doc.document_id);
            setDocuments((prev) =>
              prev.filter((d) => d.document_id !== doc.document_id),
            );
            invalidateReadiness();
          } catch {
            // 글로벌 핸들링
          }
        },
      });
    },
    [projectId, overlay, invalidateReadiness],
  );

  // 텍스트 입력 제출
  const handleTextSubmit = useCallback(async () => {
    const trimmedContent = textContent.trim();
    if (!trimmedContent) return;

    const now = new Date();
    const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
    const title = `${projectName}_knowledge_${ts}`;

    setTextSubmitting(true);
    try {
      await knowledgeService.uploadText(
        projectId,
        title,
        trimmedContent,
        false,
        textFormat,
      );
      await fetchDocuments();
      invalidateReadiness();
      setTextContent('');
    } catch {
      // 글로벌 핸들링
    } finally {
      setTextSubmitting(false);
    }
  }, [
    projectId,
    projectName,
    textContent,
    textFormat,
    fetchDocuments,
    invalidateReadiness,
  ]);

  // 카드 클릭 → 미리보기 모달
  const handleCardClick = useCallback((doc: KnowledgeDocument) => {
    if (doc.status === 'completed') {
      setPreviewTarget(doc);
    }
  }, []);

  if (showSkeleton) {
    return <ListSkeleton />;
  }

  if (loading) return null;

  return (
    <div className='flex flex-col gap-6'>
      {/* Info Banner */}
      <div className='bg-primary/5 border-primary/20 rounded-lg border p-4'>
        <p className='text-sm'>
          프로젝트에 관련 문서(PRD, 기술 스펙 등)를 업로드하면 에이전트가
          분석하여 레코드를 추출하고 SRS를 생성합니다.
        </p>
      </div>

      {/* Input Mode Tabs */}
      <div className='flex flex-col gap-4'>
        <div className='border-line-primary flex gap-1 border-b'>
          {INPUT_MODES.map((mode) => {
            const Icon = mode.icon;
            return (
              <button
                key={mode.value}
                onClick={() => setInputMode(mode.value)}
                className={cn(
                  'flex items-center gap-1.5 px-4 py-2 text-sm font-medium transition-colors',
                  inputMode === mode.value
                    ? 'text-accent-primary border-accent-primary border-b-2'
                    : 'text-fg-muted hover:text-fg-secondary',
                )}
              >
                <Icon className='size-4' />
                {mode.label}
              </button>
            );
          })}
        </div>

        {/* File Upload Area */}
        {inputMode === 'file' && (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              'flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 transition-colors',
              dragging
                ? 'border-accent-primary bg-accent-primary/5'
                : 'border-line-primary hover:border-fg-muted hover:bg-canvas-surface/50',
              uploading && 'pointer-events-none opacity-50',
            )}
          >
            <div className='bg-canvas-surface mb-3 flex size-12 items-center justify-center rounded-full'>
              {uploading ? (
                <Spinner size='size-5' className='text-fg-muted' />
              ) : (
                <Upload className='text-fg-muted size-5' />
              )}
            </div>
            <p className='text-fg-primary text-sm font-medium'>
              {uploading
                ? '업로드 중...'
                : '파일을 드래그하거나 클릭하여 업로드'}
            </p>
            <p className='text-fg-muted mt-1 text-xs'>TXT, PDF, MD</p>
            <input
              ref={fileInputRef}
              type='file'
              className='hidden'
              multiple
              accept='.pdf,.md,.txt'
              onChange={handleFileSelect}
            />
          </div>
        )}

        {/* Text Input Area */}
        {inputMode === 'text' && (
          <div className='flex flex-col gap-3'>
            <Textarea
              placeholder='텍스트를 붙여넣거나 입력하세요...'
              value={textContent}
              onChange={(e) => setTextContent(e.target.value)}
              rows={8}
              className='field-sizing-fixed min-h-20'
            />
            <div className='flex items-center justify-between'>
              <p className='text-fg-muted text-xs'>
                {textContent.length > 0 &&
                  `${textContent.length.toLocaleString()}자`}
              </p>
              <div className='flex items-center gap-2'>
                <ToggleGroup
                  type='single'
                  value={textFormat}
                  onValueChange={(v) => {
                    if (v) setTextFormat(v as 'txt' | 'md');
                  }}
                  variant='outline'
                  size='sm'
                >
                  <ToggleGroupItem value='txt' className='text-xs'>
                    텍스트
                  </ToggleGroupItem>
                  <ToggleGroupItem value='md' className='text-xs'>
                    마크다운
                  </ToggleGroupItem>
                </ToggleGroup>
                <Button
                  onClick={handleTextSubmit}
                  disabled={!textContent.trim() || textSubmitting}
                  className='gap-1.5'
                >
                  {textSubmitting ? (
                    <Spinner />
                  ) : (
                    <Upload className='size-4' />
                  )}
                  {textSubmitting ? '저장 중...' : '문서로 저장'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Document List */}
      {documents.length > 0 && (
        <div className='flex flex-col gap-2'>
          <h3 className='text-fg-primary text-sm font-semibold'>
            문서 {documents.length}개
          </h3>
          <div className='border-line-primary divide-line-primary divide-y rounded-lg border'>
            {documents.map((doc) => {
              const fileType = doc.file_type as KnowledgeDocumentFileType;
              const Icon = FILE_TYPE_ICON[fileType] ?? FileText;
              const statusConfig = STATUS_CONFIG[doc.status];
              const StatusIcon = statusConfig.icon;
              const isClickable = doc.status === 'completed';
              return (
                <div
                  key={doc.document_id}
                  onClick={() => handleCardClick(doc)}
                  className={cn(
                    'flex items-center gap-3 px-4 py-3 transition-colors',
                    isClickable && 'hover:bg-canvas-surface/70 cursor-pointer',
                  )}
                >
                  {/* File type icon */}
                  <div
                    className={cn(
                      'flex size-9 shrink-0 items-center justify-center rounded-md',
                      FILE_TYPE_COLOR[fileType] ??
                        'bg-gray-500/10 text-gray-600',
                    )}
                  >
                    <Icon className='size-4' />
                  </div>

                  {/* Name + size */}
                  <div className='min-w-0 flex-1'>
                    <p className='text-fg-primary truncate text-sm font-medium'>
                      {doc.name}
                    </p>
                    <div className='text-fg-muted flex items-center gap-2 text-xs'>
                      <span>{formatFileSize(doc.size_bytes)}</span>
                      {doc.status === 'completed' && (
                        <span>· {doc.chunk_count}개 청크</span>
                      )}
                    </div>
                  </div>

                  {/* Status badge */}
                  {doc.status === 'failed' && doc.error_message ? (
                    <HoverCard openDelay={200}>
                      <HoverCardTrigger asChild>
                        <Badge
                          variant='outline'
                          className={cn(
                            'shrink-0 cursor-pointer px-2 text-xs [&>svg]:size-4',
                            statusConfig.color,
                          )}
                        >
                          <StatusIcon />
                          {statusConfig.label}
                        </Badge>
                      </HoverCardTrigger>
                      <HoverCardContent className='w-72 text-sm'>
                        <p className='text-fg-muted mb-1 text-xs font-medium'>
                          오류 메시지
                        </p>
                        <p className='text-xs wrap-break-word text-red-500'>
                          {doc.error_message}
                        </p>
                      </HoverCardContent>
                    </HoverCard>
                  ) : (
                    <Badge
                      variant='outline'
                      className={cn(
                        'shrink-0 px-2 text-xs [&>svg]:size-4',
                        statusConfig.color,
                      )}
                    >
                      <StatusIcon
                        className={cn(
                          '',
                          doc.status === 'processing' && 'animate-spin',
                        )}
                      />
                      {statusConfig.label}
                    </Badge>
                  )}

                  {/* Active toggle */}
                  <div onClick={(e) => e.stopPropagation()}>
                    <Switch
                      checked={doc.is_active}
                      onCheckedChange={() => handleToggle(doc)}
                      className='flex shrink-0'
                      aria-label={doc.is_active ? '비활성화' : '활성화'}
                    />
                  </div>

                  {/* Actions */}
                  <div className='flex shrink-0 items-center gap-1'>
                    {doc.status === 'failed' && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant='ghost'
                            size='icon'
                            className='text-fg-muted hover:text-fg-primary size-8'
                            onClick={(e) => handleReprocess(e, doc)}
                          >
                            <RefreshCw className='size-3.5' />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>재시도</TooltipContent>
                      </Tooltip>
                    )}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant='ghost'
                          size='icon'
                          className='text-fg-muted hover:text-destructive size-8'
                          onClick={(e) => handleDelete(e, doc)}
                        >
                          <Trash2 className='size-3.5' />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>삭제</TooltipContent>
                    </Tooltip>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {documents.length === 0 && (
        <div className='flex flex-col items-center justify-center py-12 text-center'>
          <div className='bg-canvas-surface mb-4 flex size-16 items-center justify-center rounded-full'>
            <FileText className='text-fg-muted size-6' />
          </div>
          <p className='text-fg-primary text-sm font-medium'>
            아직 업로드된 문서가 없습니다
          </p>
          <p className='text-fg-muted mt-1 text-sm'>
            위 영역에 파일을 드래그하거나 클릭하여 업로드하세요
          </p>
        </div>
      )}

      {/* Preview Modal */}
      <KnowledgePreviewModal
        document={previewTarget}
        projectId={projectId}
        onClose={() => setPreviewTarget(null)}
      />
    </div>
  );
}
