'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { SrsSection } from '@/types/project';

export const SRS_SECTION_EDITOR_FORM_ID = 'srs-section-editor-form';

const schema = z.object({
  content: z.string().trim().min(1, '내용을 입력하세요'),
});

export type SrsSectionEditorValues = z.infer<typeof schema>;

interface SrsSectionEditorProps {
  section: SrsSection;
  onSubmit: (values: SrsSectionEditorValues) => void;
}

export function SrsSectionEditor({ section, onSubmit }: SrsSectionEditorProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SrsSectionEditorValues>({
    resolver: zodResolver(schema),
    defaultValues: { content: section.content },
  });

  return (
    <form
      id={SRS_SECTION_EDITOR_FORM_ID}
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className='space-y-3'
    >
      <div className='text-fg-muted text-[11px]'>
        <span className='text-fg-secondary font-medium'>{section.title}</span>
      </div>
      <div className='space-y-1'>
        <label
          className='text-fg-secondary text-xs font-medium'
          htmlFor='srs-section-editor-content'
        >
          섹션 내용 (Markdown)
        </label>
        <Textarea
          id='srs-section-editor-content'
          {...register('content')}
          rows={16}
          className={cn(
            'resize-none font-mono text-sm',
            errors.content && 'border-destructive',
          )}
        />
        {errors.content && (
          <p className='text-destructive text-xs'>{errors.content.message}</p>
        )}
      </div>
    </form>
  );
}

interface SrsSectionEditorActionsProps {
  onCancel: () => void;
  isSaving?: boolean;
}

export function SrsSectionEditorActions({
  onCancel,
  isSaving,
}: SrsSectionEditorActionsProps) {
  return (
    <div className='flex justify-end gap-2'>
      <Button type='button' variant='outline' onClick={onCancel} disabled={isSaving}>
        취소
      </Button>
      <Button type='submit' form={SRS_SECTION_EDITOR_FORM_ID} disabled={isSaving}>
        저장
      </Button>
    </div>
  );
}
