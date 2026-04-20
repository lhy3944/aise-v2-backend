'use client';

import { FlaskConical } from 'lucide-react';

export function TestCaseArtifact() {
  return (
    <div className='flex h-full items-center justify-center p-6'>
      <div className='text-center'>
        <FlaskConical className='text-fg-muted mx-auto mb-3 size-10' />
        <p className='text-fg-secondary text-sm font-medium'>Test Cases</p>
        <p className='text-fg-muted mt-1 text-xs'>
          요구사항 기반 테스트 케이스가 여기에 표시됩니다.
        </p>
      </div>
    </div>
  );
}
