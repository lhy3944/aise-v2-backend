'use client';

import { Layers } from 'lucide-react';

export function DesignArtifact() {
  return (
    <div className='flex h-full items-center justify-center p-6'>
      <div className='text-center'>
        <Layers className='text-fg-muted mx-auto mb-3 size-10' />
        <p className='text-fg-secondary text-sm font-medium'>Design</p>
        <p className='text-fg-muted mt-1 text-xs'>
          SRS 기반 설계 산출물이 여기에 표시됩니다.
        </p>
      </div>
    </div>
  );
}
