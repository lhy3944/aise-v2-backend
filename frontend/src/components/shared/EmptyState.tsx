import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      {Icon && (
        <div className='bg-muted mb-4 flex size-12 items-center justify-center rounded-full'>
          <Icon className='text-fg-muted size-6' />
        </div>
      )}
      <h3 className='text-fg-primary text-sm font-medium'>{title}</h3>
      {description && <p className='text-fg-muted mt-1 max-w-sm text-sm'>{description}</p>}
      {action && <div className='mt-4'>{action}</div>}
    </div>
  );
}
