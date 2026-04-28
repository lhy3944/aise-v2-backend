'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  ManualRecordForm,
  type ManualRecordFormValues,
} from '@/components/artifacts/ManualRecordForm';
import { ManualRecordFormActions } from '@/components/artifacts/ManualRecordFormActions';
import { artifactRecordService } from '@/services/artifact-record-service';
import type { ArtifactRecordCreate } from '@/types/project';
import { useState } from 'react';

interface ManualRecordModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  defaultSectionId?: string | null;
  /** 생성 성공 시 호출 — Records 패널이 fetch refresh 등에 사용. */
  onCreated?: () => void;
  /** 생성 실패 시 호출 (에러 메시지). 기본 처리 없으면 console.error 만. */
  onError?: (message: string) => void;
}

export function ManualRecordModal({
  open,
  onOpenChange,
  projectId,
  defaultSectionId,
  onCreated,
  onError,
}: ManualRecordModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleValidSubmit = async (values: ManualRecordFormValues) => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      const payload: ArtifactRecordCreate = {
        content: values.content,
        section_id: values.section_id,
        source_location: values.source_location?.trim() || undefined,
      };
      await artifactRecordService.create(projectId, payload);
      onCreated?.();
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : '레코드 추가에 실패했습니다';
      if (onError) onError(msg);
      else console.error('[ManualRecordModal] create failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (isSubmitting) return;
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !isSubmitting && onOpenChange(o)}>
      <DialogContent className='flex flex-col gap-0 p-0 sm:max-w-[520px]'>
        <DialogHeader className='border-line-primary border-b p-6 pb-4'>
          <DialogTitle className='text-fg-primary'>
            레코드 직접 추가
          </DialogTitle>
          <DialogDescription>
            섹션을 선택하고 요구사항 본문을 직접 입력하세요. 추가된 레코드는
            &apos;수동 입력&apos; 으로 표시됩니다.
          </DialogDescription>
        </DialogHeader>
        <div className='flex-1 overflow-y-auto p-6'>
          {open && (
            <ManualRecordForm
              projectId={projectId}
              defaultSectionId={defaultSectionId}
              onValidSubmit={handleValidSubmit}
            />
          )}
        </div>
        <DialogFooter className='border-line-primary border-t p-4'>
          <ManualRecordFormActions
            onCancel={handleCancel}
            isSubmitting={isSubmitting}
          />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
