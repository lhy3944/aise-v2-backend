'use client';

import { cn } from '@/lib/utils';

interface WaveDotsProps {
  className?: string;
  dotClassName?: string;
}

export function WaveDots({ className, dotClassName }: WaveDotsProps) {
  return (
    <div
      className={cn('inline-flex items-end gap-1 text-fg-muted', className)}
      aria-hidden
    >
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className={cn(
            'size-0.5 rounded-full bg-current animate-[wave-dot_1s_ease-in-out_infinite]',
            dotClassName,
          )}
          style={{ animationDelay: `${index * 150}ms` }}
        />
      ))}

      <style jsx>{`
        @keyframes wave-dot {
          0%,
          100% {
            transform: translateY(0);
            opacity: 0.8;
          }
          50% {
            transform: translateY(3px);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
