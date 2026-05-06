import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface ArtifactEmptyGuideItem {
  icon: LucideIcon;
  title: string;
  description: string;
}

interface ArtifactEmptyGuideProps {
  icon: LucideIcon;
  title: string;
  description: string;
  guides: ArtifactEmptyGuideItem[];
  action?: ReactNode;
  errorMessage?: string | null;
}

export function ArtifactEmptyGuide({
  icon: Icon,
  title,
  description,
  guides,
  action,
  errorMessage,
}: ArtifactEmptyGuideProps) {
  return (
    <div className='flex h-full items-start justify-center px-5 pt-10 pb-5'>
      <div className='w-full max-w-sm'>
        <div className='text-center'>
          <div className='border-line-primary bg-canvas-surface mx-auto mb-4 flex size-12 items-center justify-center rounded-lg border shadow-xs'>
            <Icon className='text-accent-primary size-5' />
          </div>
          <p className='text-fg-primary text-sm font-semibold'>{title}</p>
          <p className='text-fg-muted mx-auto mt-2 max-w-full text-xs leading-relaxed whitespace-nowrap'>
            {description}
          </p>
        </div>

        <div className='mt-5 space-y-2'>
          {guides.map((item) => {
            const GuideIcon = item.icon;
            return (
              <div
                key={item.title}
                className='border-line-subtle bg-canvas-surface/60 flex items-start gap-3 rounded-lg border px-3 py-2.5'
              >
                <span className='border-line-primary bg-canvas-primary mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border'>
                  <GuideIcon className='text-fg-secondary size-3.5' />
                </span>
                <span className='min-w-0'>
                  <span className='text-fg-primary block text-xs font-medium'>
                    {item.title}
                  </span>
                  <span className='text-fg-muted mt-0.5 block text-[11px] leading-relaxed'>
                    {item.description}
                  </span>
                </span>
              </div>
            );
          })}
        </div>

        {action && <div className='mt-5 flex justify-center'>{action}</div>}
        {errorMessage && (
          <p className='text-destructive mt-3 text-center text-xs'>
            {errorMessage}
          </p>
        )}
      </div>
    </div>
  );
}
