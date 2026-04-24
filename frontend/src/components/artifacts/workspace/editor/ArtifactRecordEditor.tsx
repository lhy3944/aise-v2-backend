'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { ArtifactRecord } from '@/types/project';

export const ARTIFACT_RECORD_EDITOR_FORM_ID = 'artifact-record-editor-form';

const schema = z.object({
  content: z.string().trim().min(1, '내용을 입력하세요'),
});

export type ArtifactRecordEditorValues = z.infer<typeof schema>;

interface ArtifactRecordEditorProps {
  record: ArtifactRecord;
  /** 이전에 저장된 드래프트가 있으면 기본값으로 사용 */
  draftContent?: string;
  onSubmit: (values: ArtifactRecordEditorValues) => void;
}

export function ArtifactRecordEditor({
  record,
  draftContent,
  onSubmit,
}: ArtifactRecordEditorProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ArtifactRecordEditorValues>({
    resolver: zodResolver(schema),
    defaultValues: { content: draftContent ?? record.content },
  });

  return (
    <form
      id={ARTIFACT_RECORD_EDITOR_FORM_ID}
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className='space-y-3'
    >
      <div className='text-fg-muted flex items-center gap-2 text-[11px]'>
        <span className='text-fg-secondary font-mono font-medium'>{record.display_id}</span>
        {record.section_name && (
          <>
            <span className='opacity-40'>·</span>
            <span>{record.section_name}</span>
          </>
        )}
      </div>
      <div className='space-y-1'>
        <label
          className='text-fg-secondary text-xs font-medium'
          htmlFor='artifact-record-editor-content'
        >
          내용
        </label>
        <Textarea
          id='artifact-record-editor-content'
          {...register('content')}
          rows={6}
          className={cn('resize-none text-sm', errors.content && 'border-destructive')}
        />
        {errors.content && (
          <p className='text-destructive text-xs'>{errors.content.message}</p>
        )}
      </div>
    </form>
  );
}

interface ArtifactRecordEditorActionsProps {
  hasDraft: boolean;
  onCancel: () => void;
  onDiscard: () => void;
}

export function ArtifactRecordEditorActions({
  hasDraft,
  onCancel,
  onDiscard,
}: ArtifactRecordEditorActionsProps) {
  return (
    <div className='flex items-center justify-between gap-2'>
      {hasDraft ? (
        <Button
          type='button'
          variant='ghost'
          className='text-destructive hover:text-destructive'
          onClick={onDiscard}
        >
          드래프트 폐기
        </Button>
      ) : (
        <span />
      )}
      <div className='flex gap-2'>
        <Button type='button' variant='outline' onClick={onCancel}>
          취소
        </Button>
        <Button type='submit' form={ARTIFACT_RECORD_EDITOR_FORM_ID}>
          저장
        </Button>
      </div>
    </div>
  );
}
