'use client';

import { FileText } from 'lucide-react';

export function SrsArtifact() {
  return (
    <div className='flex h-full items-center justify-center p-6'>
      <div className='text-center'>
        <FileText className='text-fg-muted mx-auto mb-3 size-10' />
        <p className='text-fg-secondary text-sm font-medium'>SRS 문서</p>
        <p className='text-fg-muted mt-1 text-xs'>요구사항 Review 후 SRS를 생성할 수 있습니다.</p>
      </div>
    </div>
  );
}
