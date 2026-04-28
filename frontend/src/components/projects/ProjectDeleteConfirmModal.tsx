'use client';

import { AlertTriangle, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/utils';
import { projectService } from '@/services/project-service';
import type { ProjectDeletePreview } from '@/types/project';

interface ProjectDeleteConfirmModalProps {
  projectId: string;
  projectName: string;
  onCancel: () => void;
  onDeleted: () => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let v = bytes;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}

const ROW_LABELS: Array<{
  key: keyof ProjectDeletePreview;
  label: string;
  format?: (v: number) => string;
}> = [
  { key: 'knowledge_documents', label: '지식 문서' },
  {
    key: 'knowledge_files_bytes',
    label: '첨부 파일 용량',
    format: formatBytes,
  },
  { key: 'sessions', label: '대화 세션' },
  { key: 'session_messages', label: '대화 메시지' },
  { key: 'artifacts', label: '산출물 (record/SRS/Design/TC)' },
  { key: 'artifact_versions', label: '버전 히스토리' },
  { key: 'pull_requests', label: 'Pull Requests' },
  { key: 'glossary_items', label: '용어집 항목' },
  { key: 'requirement_sections', label: '요구사항 섹션' },
];

export function ProjectDeleteConfirmModal({
  projectId,
  projectName,
  onCancel,
  onDeleted,
}: ProjectDeleteConfirmModalProps) {
  const [preview, setPreview] = useState<ProjectDeletePreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [confirmName, setConfirmName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    projectService
      .getDeletePreview(projectId)
      .then((res) => {
        if (!cancelled) setPreview(res);
      })
      .catch((err) => {
        if (cancelled) return;
        setPreviewError(
          err instanceof ApiError
            ? err.message
            : '영향도 미리보기 조회에 실패했습니다.',
        );
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const nameMatches = confirmName.trim() === projectName;

  async function handleDelete() {
    if (!nameMatches) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await projectService.delete(projectId, confirmName.trim());
      onDeleted();
    } catch (err) {
      setSubmitError(
        err instanceof ApiError ? err.message : '삭제에 실패했습니다.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className='flex flex-col gap-4'>
      <div className='flex gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-3'>
        <AlertTriangle className='mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400' />
        <div className='text-fg-primary text-xs leading-relaxed'>
          삭제하면 <strong>30일간 휴지통</strong>에 보관된 후 영구 삭제됩니다.
          기간 내 복원 가능하지만, 영구 삭제 후에는 아래 항목이 모두 사라집니다.
        </div>
      </div>

      {/* 영향 카운트 표 */}
      <div className='border-line-primary overflow-hidden rounded-md border'>
        <div className='border-line-primary text-fg-secondary border-b px-3 py-1.5 text-[11px] font-semibold tracking-wider uppercase'>
          영향받는 데이터
        </div>
        {previewError && (
          <p className='text-destructive px-3 py-2 text-xs'>{previewError}</p>
        )}
        {!preview && !previewError && (
          <div className='text-fg-muted flex items-center gap-2 px-3 py-3 text-xs'>
            <Loader2 className='size-3.5 animate-spin' />
            영향도 분석 중...
          </div>
        )}
        {preview && (
          <ul className='divide-line-primary divide-y'>
            {ROW_LABELS.map(({ key, label, format }) => {
              const value = preview[key] as number;
              return (
                <li
                  key={key}
                  className='flex items-center justify-between px-3 py-1.5 text-xs'
                >
                  <span className='text-fg-secondary'>{label}</span>
                  <span
                    className={cn(
                      'font-mono tabular-nums',
                      value > 0 ? 'text-fg-primary' : 'text-fg-muted/60',
                    )}
                  >
                    {format ? format(value) : value.toLocaleString()}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* type-to-confirm */}
      <div className='space-y-1.5'>
        <label
          htmlFor='delete-confirm-name'
          className='text-fg-secondary block text-xs font-medium'
        >
          삭제하려면 프로젝트 이름{' '}
          <span className='text-fg-primary font-mono font-semibold'>
            {projectName}
          </span>
          을(를) 입력하세요
        </label>
        <Input
          id='delete-confirm-name'
          autoComplete='off'
          autoFocus
          placeholder={projectName}
          value={confirmName}
          onChange={(e) => setConfirmName(e.target.value)}
          className={cn(
            'h-9 text-sm',
            confirmName.length > 0 && !nameMatches && 'border-destructive',
          )}
        />
        {confirmName.length > 0 && !nameMatches && (
          <p className='text-destructive text-xs'>이름이 일치하지 않습니다.</p>
        )}
      </div>

      {submitError && (
        <p className='text-destructive text-xs'>{submitError}</p>
      )}

      <div className='flex justify-end gap-2'>
        <Button variant='outline' size='sm' onClick={onCancel} disabled={submitting}>
          취소
        </Button>
        <Button
          variant='destructive'
          size='sm'
          onClick={handleDelete}
          disabled={!nameMatches || submitting}
          className='gap-1.5'
        >
          {submitting && <Loader2 className='size-3.5 animate-spin' />}
          휴지통으로 이동
        </Button>
      </div>
    </div>
  );
}
