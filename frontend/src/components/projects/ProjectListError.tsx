import { Button } from '@/components/ui/button';
import { RefreshCcw, ServerCrash } from 'lucide-react';

interface ProjectListErrorProps {
  message: string;
  onRetry: () => void;
}

export function ProjectListError({ message, onRetry }: ProjectListErrorProps) {
  return (
    <div className='animate-in fade-in flex min-h-[calc(100vh-14rem)] flex-col items-center justify-center text-center duration-300'>
      <div className='bg-canvas-surface mb-4 flex size-16 items-center justify-center rounded-full'>
        <ServerCrash className='text-fg-muted size-6' />
      </div>
      <h2 className='text-fg-primary text-base font-medium'>
        프로젝트 목록을 불러올 수 없습니다
      </h2>
      <p className='text-fg-secondary mb-6 text-sm'>{message}</p>
      <Button variant='outline' onClick={onRetry}>
        <RefreshCcw />
        다시 시도
      </Button>
    </div>
  );
}
