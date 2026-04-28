'use client';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { MANUAL_RECORD_FORM_ID } from '@/components/artifacts/ManualRecordForm';

interface ManualRecordFormActionsProps {
  onCancel: () => void;
  isSubmitting: boolean;
}

export function ManualRecordFormActions({
  onCancel,
  isSubmitting,
}: ManualRecordFormActionsProps) {
  return (
    <div className='flex justify-end gap-2'>
      <Button variant='outline' onClick={onCancel} disabled={isSubmitting}>
        취소
      </Button>
      <Button
        type='submit'
        form={MANUAL_RECORD_FORM_ID}
        disabled={isSubmitting}
      >
        {isSubmitting && <Spinner size='size-4' className='mr-1' />}
        추가
      </Button>
    </div>
  );
}
