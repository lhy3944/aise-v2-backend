'use client';

import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';
import { sectionService } from '@/services/section-service';
import type { Section } from '@/types/project';
import { cn } from '@/lib/utils';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { z } from 'zod';

export const MANUAL_RECORD_FORM_ID = 'manual-record-form';

const schema = z.object({
  section_id: z.string().uuid({ message: '섹션을 선택해주세요' }),
  content: z
    .string()
    .trim()
    .min(5, '최소 5자 이상 입력해주세요')
    .max(2000, '최대 2000자까지 입력 가능합니다'),
  source_location: z
    .string()
    .trim()
    .max(200, '최대 200자까지 입력 가능합니다')
    .optional()
    .or(z.literal('')),
});

export type ManualRecordFormValues = z.infer<typeof schema>;

interface ManualRecordFormProps {
  projectId: string;
  defaultSectionId?: string | null;
  onValidSubmit: (values: ManualRecordFormValues) => Promise<void> | void;
}

export function ManualRecordForm({
  projectId,
  defaultSectionId,
  onValidSubmit,
}: ManualRecordFormProps) {
  const [sections, setSections] = useState<Section[]>([]);
  const [loadingSections, setLoadingSections] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<ManualRecordFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      section_id: defaultSectionId ?? '',
      content: '',
      source_location: '',
    },
  });

  useEffect(() => {
    let cancelled = false;
    sectionService
      .list(projectId)
      .then((res) => {
        if (cancelled) return;
        const active = res.sections.filter((s) => s.is_active);
        setSections(active);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setLoadError(
          err instanceof Error
            ? err.message
            : '섹션 목록을 불러오지 못했습니다',
        );
      })
      .finally(() => {
        if (!cancelled) setLoadingSections(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  return (
    <form
      id={MANUAL_RECORD_FORM_ID}
      onSubmit={handleSubmit(onValidSubmit)}
      noValidate
      className='space-y-4'
    >
      {/* 섹션 선택 */}
      <div className='space-y-1.5'>
        <label className='text-fg-primary text-sm font-medium'>
          섹션 <span className='text-destructive'>*</span>
        </label>
        {loadingSections ? (
          <div className='border-line-primary text-fg-muted flex items-center gap-2 rounded-md border px-3 py-2 text-sm'>
            <Spinner size='size-4' /> 섹션을 불러오는 중…
          </div>
        ) : loadError ? (
          <p className='text-destructive text-xs'>{loadError}</p>
        ) : sections.length === 0 ? (
          <p className='text-fg-muted text-xs'>
            활성 섹션이 없습니다. 먼저 좌측 &apos;요구사항 섹션&apos; 에서
            섹션을 활성화해주세요.
          </p>
        ) : (
          <Controller
            name='section_id'
            control={control}
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger
                  className={cn(errors.section_id && 'border-destructive')}
                >
                  <SelectValue placeholder='섹션을 선택하세요' />
                </SelectTrigger>
                <SelectContent>
                  {sections.map((s) => (
                    <SelectItem key={s.section_id} value={s.section_id}>
                      {s.name}
                      <span className='text-fg-muted ml-2 text-xs'>
                        ({s.type})
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
        )}
        {errors.section_id && (
          <p className='text-destructive text-xs'>
            {errors.section_id.message}
          </p>
        )}
      </div>

      {/* 본문 */}
      <div className='space-y-1.5'>
        <label className='text-fg-primary text-sm font-medium'>
          내용 <span className='text-destructive'>*</span>
        </label>
        <Textarea
          {...register('content')}
          rows={5}
          placeholder='예: 사용자는 OAuth 2.0 으로 로그인할 수 있어야 한다.'
          className={cn(errors.content && 'border-destructive')}
        />
        {errors.content && (
          <p className='text-destructive text-xs'>{errors.content.message}</p>
        )}
      </div>

      {/* 출처 (선택) */}
      <div className='space-y-1.5'>
        <label className='text-fg-secondary text-sm'>
          출처 <span className='text-fg-muted text-xs'>(선택)</span>
        </label>
        <Input
          {...register('source_location')}
          placeholder='예: 외부 표준 문서, 회의록 2024-03-15'
          className={cn(errors.source_location && 'border-destructive')}
        />
        {errors.source_location && (
          <p className='text-destructive text-xs'>
            {errors.source_location.message}
          </p>
        )}
      </div>
    </form>
  );
}
