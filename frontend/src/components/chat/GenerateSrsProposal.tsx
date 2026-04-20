'use client';

import { useState } from 'react';
import { Spinner } from '@/components/ui/spinner';
import { FileText, Play } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface GenerateSrsProposalProps {
  data: {
    title: string;
    summary: string;
    requirement_count: number;
    sections: string[];
  };
  onConfirm: () => void;
}

export function GenerateSrsProposal({ data, onConfirm }: GenerateSrsProposalProps) {
  const [confirmed, setConfirmed] = useState(false);

  const handleConfirm = () => {
    setConfirmed(true);
    onConfirm();
  };

  return (
    <div className='bg-canvas-surface border-accent-primary/20 w-full rounded-xl border p-4'>
      <div className='mb-3 flex items-center gap-2'>
        <FileText className='text-accent-primary size-4' />
        <span className='text-fg-primary text-sm font-medium'>SRS 문서 생성 제안</span>
      </div>

      <div className='bg-canvas-primary mb-3 rounded-lg p-3'>
        <h4 className='text-fg-primary text-sm font-medium'>{data.title}</h4>
        <p className='text-fg-secondary mt-1 text-xs'>{data.summary}</p>

        <div className='mt-2 flex items-center gap-2'>
          <Badge variant='secondary' className='text-xs'>
            요구사항 {data.requirement_count}개
          </Badge>
          <Badge variant='secondary' className='text-xs'>
            섹션 {data.sections.length}개
          </Badge>
        </div>

        {data.sections.length > 0 && (
          <div className='mt-2'>
            <p className='text-fg-muted mb-1 text-xs'>포함 섹션:</p>
            <ul className='text-fg-secondary list-inside list-disc text-xs'>
              {data.sections.map((section) => (
                <li key={section}>{section}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {confirmed ? (
        <div className='text-accent-primary flex items-center gap-2 text-sm'>
          <Spinner />
          SRS 문서를 생성하고 있습니다...
        </div>
      ) : (
        <div className='flex gap-2'>
          <Button size='sm' onClick={handleConfirm} className='gap-1.5'>
            <Play className='size-3.5' />
            SRS 생성 시작
          </Button>
        </div>
      )}
    </div>
  );
}
