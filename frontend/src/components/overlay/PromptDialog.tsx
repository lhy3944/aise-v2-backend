'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import {
  AlertDialog as AlertDialogRoot,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { PromptOptions } from '@/stores/overlay-store';

const FORM_ID = 'overlay-prompt-form';

interface PromptDialogProps extends PromptOptions {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type PromptFormValues = { value: string };

export function PromptDialog({
  open,
  onOpenChange,
  title,
  description,
  label,
  placeholder,
  defaultValue = '',
  confirmLabel = '확인',
  cancelLabel = '취소',
  requiredMessage = '값을 입력하세요',
  maxLength,
  onConfirm,
  onCancel,
}: PromptDialogProps) {
  const schema = z.object({
    value: (() => {
      let s = z.string().trim().min(1, requiredMessage);
      if (maxLength) s = s.max(maxLength, `${maxLength}자 이내로 입력하세요`);
      return s;
    })(),
  });

  const {
    register,
    handleSubmit,
    reset,
    setFocus,
    formState: { errors },
  } = useForm<PromptFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { value: defaultValue },
  });

  const confirmedRef = useRef(false);

  useEffect(() => {
    if (open) {
      confirmedRef.current = false;
      reset({ value: defaultValue });
      const t = setTimeout(() => setFocus('value', { shouldSelect: true }), 50);
      return () => clearTimeout(t);
    }
  }, [open, defaultValue, reset, setFocus]);

  const handleOpenChange = (next: boolean) => {
    if (!next && !confirmedRef.current) onCancel?.();
    onOpenChange(next);
  };

  const handleCancel = () => {
    onCancel?.();
    confirmedRef.current = true;
    onOpenChange(false);
  };

  const onSubmit = (data: PromptFormValues) => {
    confirmedRef.current = true;
    onConfirm(data.value.trim());
    onOpenChange(false);
  };

  return (
    <AlertDialogRoot open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent className='max-w-[420px]'>
        <AlertDialogHeader>
          <AlertDialogTitle className='text-fg-primary'>
            {title}
          </AlertDialogTitle>
          {description && (
            <AlertDialogDescription>{description}</AlertDialogDescription>
          )}
        </AlertDialogHeader>

        <form
          id={FORM_ID}
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          className='space-y-1.5'
        >
          {label && (
            <label
              htmlFor='overlay-prompt-input'
              className='text-fg-secondary text-xs'
            >
              {label}
            </label>
          )}
          <Input
            id='overlay-prompt-input'
            placeholder={placeholder}
            className={cn(errors.value && 'border-destructive')}
            {...register('value')}
          />
          {errors.value && (
            <p className='text-destructive text-xs'>{errors.value.message}</p>
          )}
        </form>

        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleCancel}>
            {cancelLabel}
          </AlertDialogCancel>
          <Button type='submit' form={FORM_ID}>
            {confirmLabel}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialogRoot>
  );
}
