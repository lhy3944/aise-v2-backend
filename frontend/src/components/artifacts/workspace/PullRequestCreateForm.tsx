'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

export const PR_CREATE_FORM_ID = 'pr-create-form';

const schema = z.object({
  title: z
    .string()
    .trim()
    .min(1, '커밋 메시지를 입력하세요')
    .max(200, '200자 이내로 작성하세요'),
  description: z.string().trim().optional(),
});

export type PullRequestCreateValues = z.infer<typeof schema>;

export interface StagedChangeSummary {
  artifactId: string;
  displayId: string;
  contentPreview: string;
}

interface PullRequestCreateFormProps {
  changes: StagedChangeSummary[];
  onSubmit: (values: PullRequestCreateValues) => void;
  defaultTitle?: string;
}

export function PullRequestCreateForm({
  changes,
  onSubmit,
  defaultTitle,
}: PullRequestCreateFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PullRequestCreateValues>({
    resolver: zodResolver(schema),
    defaultValues: { title: defaultTitle ?? '', description: '' },
  });

  return (
    <form
      id={PR_CREATE_FORM_ID}
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      className='space-y-4'
    >
      <div className='space-y-1'>
        <label className='text-fg-secondary text-xs font-medium' htmlFor='pr-title'>
          커밋 메시지 <span className='text-destructive'>*</span>
        </label>
        <Input
          id='pr-title'
          placeholder='예: FR-003 다크모드 토글 요구사항 보강'
          className={cn(errors.title && 'border-destructive')}
          {...register('title')}
        />
        {errors.title && (
          <p className='text-destructive text-xs'>{errors.title.message}</p>
        )}
      </div>

      <div className='space-y-1'>
        <label
          className='text-fg-secondary text-xs font-medium'
          htmlFor='pr-description'
        >
          설명 (선택)
        </label>
        <Textarea
          id='pr-description'
          rows={3}
          placeholder='변경 사유, 영향 범위 등을 기록합니다'
          className='resize-none text-sm'
          {...register('description')}
        />
      </div>

      <div className='border-line-primary rounded-md border p-2'>
        <p className='text-fg-secondary mb-2 text-[11px] font-semibold'>
          포함되는 변경 ({changes.length})
        </p>
        <ul className='flex flex-col gap-1'>
          {changes.map((c) => (
            <li
              key={c.artifactId}
              className='flex items-start gap-2 text-[11px] leading-snug'
            >
              <span className='text-fg-secondary shrink-0 font-mono font-medium'>
                {c.displayId}
              </span>
              <span className='text-fg-muted line-clamp-1'>{c.contentPreview}</span>
            </li>
          ))}
        </ul>
      </div>
    </form>
  );
}

interface PullRequestCreateActionsProps {
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function PullRequestCreateActions({
  onCancel,
  isSubmitting,
}: PullRequestCreateActionsProps) {
  return (
    <div className='flex justify-end gap-2'>
      <Button
        type='button'
        variant='outline'
        onClick={onCancel}
        disabled={isSubmitting}
      >
        취소
      </Button>
      <Button type='submit' form={PR_CREATE_FORM_ID} disabled={isSubmitting}>
        {isSubmitting ? 'PR 생성 중...' : 'PR 생성'}
      </Button>
    </div>
  );
}
