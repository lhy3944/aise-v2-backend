'use client';

import { ModuleGraph } from '@/components/projects/ModuleGraph';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { ProjectCreate, ProjectModule } from '@/types/project';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

const MODULE_PRESETS: { label: string; modules: ProjectModule[] }[] = [
  { label: 'All', modules: ['requirements', 'design', 'testcase'] },
  { label: 'Requirements Only', modules: ['requirements'] },
  { label: 'Req + Design', modules: ['requirements', 'design'] },
  { label: 'Req + Testcase', modules: ['requirements', 'testcase'] },
  { label: 'Testcase Only', modules: ['testcase'] },
];

const FORM_ID = 'project-create-form';

const projectCreateSchema = z.object({
  name: z.string().trim().min(1, '프로젝트 이름을 입력하세요'),
  description: z.string().optional(),
  domain: z.string().optional(),
  product_type: z.string().optional(),
  modules: z
    .array(z.enum(['requirements', 'design', 'testcase']))
    .min(1, '모듈을 하나 이상 선택하세요'),
});

type FormValues = z.infer<typeof projectCreateSchema>;

interface ProjectCreateFormProps {
  onSubmit: (data: ProjectCreate) => void;
  initialData?: Partial<ProjectCreate>;
}

export function ProjectCreateForm({ onSubmit, initialData }: ProjectCreateFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(projectCreateSchema),
    defaultValues: {
      name: initialData?.name ?? '',
      description: initialData?.description ?? '',
      domain: initialData?.domain ?? '',
      product_type: initialData?.product_type ?? '',
      modules: initialData?.modules ?? ['requirements', 'design', 'testcase'],
    },
  });

  const modules = useWatch({ control, name: 'modules' });

  function onValid(data: FormValues) {
    onSubmit({
      name: data.name,
      description: data.description?.trim() || null,
      domain: data.domain?.trim() || null,
      product_type: data.product_type?.trim() || null,
      modules: data.modules,
    });
  }

  return (
    <form
      id={FORM_ID}
      onSubmit={handleSubmit(onValid)}
      className='flex flex-col gap-5'
      autoComplete='off'
      noValidate
    >
      {/* Name */}
      <div className='flex flex-col gap-1.5'>
        <Label htmlFor='project-name'>
          프로젝트 이름 <span className='text-destructive'>*</span>
        </Label>
        <Input
          id='project-name'
          placeholder='프로젝트 이름을 입력하세요'
          autoFocus
          {...register('name')}
          className={cn(errors.name && 'border-destructive')}
        />
        {errors.name && <p className='text-destructive text-xs'>{errors.name.message}</p>}
      </div>

      {/* Description */}
      <div className='flex flex-col gap-1.5'>
        <Label htmlFor='project-desc'>설명</Label>
        <Textarea
          id='project-desc'
          placeholder='프로젝트에 대한 간단한 설명'
          className='min-h-20 resize-none'
          {...register('description')}
        />
      </div>

      {/* Domain & Product Type */}
      <div className='grid grid-cols-2 gap-3'>
        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='project-domain'>도메인</Label>
          <Input id='project-domain' placeholder='예: robotics' {...register('domain')} />
        </div>
        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='project-product'>제품 유형</Label>
          <Input id='project-product' placeholder='예: embedded' {...register('product_type')} />
        </div>
      </div>

      {/* Module Selection */}
      <div className='flex flex-col gap-2'>
        <Label>
          모듈 선택 <span className='text-destructive'>*</span>
        </Label>

        {/* Presets */}
        <div className='flex w-full flex-wrap gap-2'>
          {MODULE_PRESETS.map((preset) => {
            const isActive =
              preset.modules.length === modules.length &&
              preset.modules.every((m) => modules.includes(m));
            return (
              <Button
                type='button'
                variant='ghost'
                key={preset.label}
                onClick={() => setValue('modules', preset.modules, { shouldValidate: true })}
                className={cn(
                  'flex-1 rounded-md border p-2 text-xs font-medium transition-colors',
                  isActive
                    ? 'border-accent-primary bg-accent-primary/5 text-accent-primary'
                    : 'border-line-primary text-fg-secondary hover:border-fg-muted',
                )}
              >
                {preset.label}
              </Button>
            );
          })}
        </div>

        {errors.modules && <p className='text-destructive text-xs'>{errors.modules.message}</p>}

        {/* Module graph */}
        <ModuleGraph modules={modules} />
      </div>
    </form>
  );
}

/** Modal footer에 배치할 외부 액션 버튼. form 속성으로 폼과 연결된다. */
export function ProjectCreateFormActions({
  onCancel,
  isLoading = false,
  disabled = false,
}: {
  onCancel: () => void;
  isLoading?: boolean;
  disabled?: boolean;
}) {
  return (
    <div className='flex justify-end gap-2'>
      <Button type='button' variant='outline' onClick={onCancel} disabled={isLoading}>
        취소
      </Button>
      <Button type='submit' form={FORM_ID} disabled={disabled || isLoading} className='w-[120px]'>
        {isLoading ? '생성중' : '프로젝트 생성'}
        {isLoading && <Spinner />}
      </Button>
    </div>
  );
}
