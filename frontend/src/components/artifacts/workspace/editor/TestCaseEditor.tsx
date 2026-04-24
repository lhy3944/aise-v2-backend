'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Trash2 } from 'lucide-react';
import { useFieldArray, useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { TestCaseContent } from '@/types/testcase';

export const TEST_CASE_EDITOR_FORM_ID = 'test-case-editor-form';

const schema = z.object({
  title: z.string().trim().min(1, '제목을 입력하세요').max(200),
  precondition: z.string(),
  steps: z
    .array(z.object({ value: z.string().trim().min(1, '내용을 입력하세요') }))
    .min(1, '최소 1개의 스텝이 필요합니다'),
  expected_result: z.string(),
  priority: z.enum(['high', 'medium', 'low']),
  type: z.enum(['functional', 'non_functional', 'boundary', 'negative']),
});

export type TestCaseEditorValues = z.infer<typeof schema>;

export interface TestCaseEditorPayload extends TestCaseContent {
  related_srs_section_id: string | null;
}

interface TestCaseEditorProps {
  initial: TestCaseContent;
  onSubmit: (values: TestCaseEditorPayload) => void;
}

export function TestCaseEditor({ initial, onSubmit }: TestCaseEditorProps) {
  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors },
  } = useForm<TestCaseEditorValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: initial.title,
      precondition: initial.precondition,
      steps: (initial.steps.length > 0 ? initial.steps : ['']).map((s) => ({
        value: s,
      })),
      expected_result: initial.expected_result,
      priority: initial.priority,
      type: initial.type,
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'steps' });
  const priority = watch('priority');
  const type = watch('type');

  const submit = (values: TestCaseEditorValues) => {
    onSubmit({
      title: values.title,
      precondition: values.precondition,
      steps: values.steps.map((s) => s.value),
      expected_result: values.expected_result,
      priority: values.priority,
      type: values.type,
      related_srs_section_id: initial.related_srs_section_id,
    });
  };

  return (
    <form
      id={TEST_CASE_EDITOR_FORM_ID}
      onSubmit={handleSubmit(submit)}
      noValidate
      className='space-y-3'
    >
      <div className='space-y-1'>
        <label className='text-fg-secondary text-xs font-medium' htmlFor='tc-title'>
          제목
        </label>
        <Input
          id='tc-title'
          {...register('title')}
          className={cn(errors.title && 'border-destructive')}
        />
        {errors.title && (
          <p className='text-destructive text-xs'>{errors.title.message}</p>
        )}
      </div>

      <div className='grid grid-cols-2 gap-3'>
        <div className='space-y-1'>
          <label className='text-fg-secondary text-xs font-medium'>우선순위</label>
          <Select
            value={priority}
            onValueChange={(v) =>
              setValue('priority', v as TestCaseEditorValues['priority'], {
                shouldValidate: true,
              })
            }
          >
            <SelectTrigger size='sm' className='h-8 w-full text-xs'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value='high' className='text-xs'>
                High
              </SelectItem>
              <SelectItem value='medium' className='text-xs'>
                Medium
              </SelectItem>
              <SelectItem value='low' className='text-xs'>
                Low
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className='space-y-1'>
          <label className='text-fg-secondary text-xs font-medium'>유형</label>
          <Select
            value={type}
            onValueChange={(v) =>
              setValue('type', v as TestCaseEditorValues['type'], {
                shouldValidate: true,
              })
            }
          >
            <SelectTrigger size='sm' className='h-8 w-full text-xs'>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value='functional' className='text-xs'>
                Functional
              </SelectItem>
              <SelectItem value='non_functional' className='text-xs'>
                Non-functional
              </SelectItem>
              <SelectItem value='boundary' className='text-xs'>
                Boundary
              </SelectItem>
              <SelectItem value='negative' className='text-xs'>
                Negative
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className='space-y-1'>
        <label
          className='text-fg-secondary text-xs font-medium'
          htmlFor='tc-precondition'
        >
          사전 조건
        </label>
        <Textarea
          id='tc-precondition'
          {...register('precondition')}
          rows={2}
          className='resize-none text-sm'
        />
      </div>

      <div className='space-y-1'>
        <div className='flex items-center justify-between'>
          <label className='text-fg-secondary text-xs font-medium'>스텝</label>
          <Button
            type='button'
            variant='ghost'
            size='sm'
            className='h-6 gap-1 px-2 text-[10px]'
            onClick={() => append({ value: '' })}
          >
            <Plus className='size-3' />
            추가
          </Button>
        </div>
        <ol className='space-y-1.5'>
          {fields.map((field, idx) => (
            <li key={field.id} className='flex items-start gap-2'>
              <span className='text-fg-muted pt-2 font-mono text-[11px] tabular-nums'>
                {idx + 1}.
              </span>
              <div className='flex-1 space-y-1'>
                <Textarea
                  {...register(`steps.${idx}.value` as const)}
                  rows={2}
                  className={cn(
                    'resize-none text-sm',
                    errors.steps?.[idx]?.value && 'border-destructive',
                  )}
                />
                {errors.steps?.[idx]?.value && (
                  <p className='text-destructive text-xs'>
                    {errors.steps[idx]?.value?.message}
                  </p>
                )}
              </div>
              <Button
                type='button'
                variant='ghost'
                size='icon'
                className='text-fg-muted hover:text-destructive mt-1 size-7'
                onClick={() => remove(idx)}
                disabled={fields.length <= 1}
              >
                <Trash2 className='size-3' />
              </Button>
            </li>
          ))}
        </ol>
        {errors.steps?.root && (
          <p className='text-destructive text-xs'>{errors.steps.root.message}</p>
        )}
      </div>

      <div className='space-y-1'>
        <label
          className='text-fg-secondary text-xs font-medium'
          htmlFor='tc-expected'
        >
          기대 결과
        </label>
        <Textarea
          id='tc-expected'
          {...register('expected_result')}
          rows={3}
          className='resize-none text-sm'
        />
      </div>
    </form>
  );
}

interface TestCaseEditorActionsProps {
  onCancel: () => void;
  isSaving?: boolean;
}

export function TestCaseEditorActions({
  onCancel,
  isSaving,
}: TestCaseEditorActionsProps) {
  return (
    <div className='flex justify-end gap-2'>
      <Button type='button' variant='outline' onClick={onCancel} disabled={isSaving}>
        취소
      </Button>
      <Button type='submit' form={TEST_CASE_EDITOR_FORM_ID} disabled={isSaving}>
        저장
      </Button>
    </div>
  );
}
