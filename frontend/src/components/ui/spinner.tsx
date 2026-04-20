import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';
import { Loader2 } from 'lucide-react';

type SpinnerVariant = 'icon' | 'ring';

interface SpinnerProps extends React.ComponentProps<'div'> {
  /** 스피너 스타일 — icon: 아이콘 회전 (기본), ring: CSS 링 애니메이션 */
  variant?: SpinnerVariant;
  /** 아이콘 컴포넌트 (variant='icon'일 때 사용, 기본: Loader2) */
  icon?: LucideIcon;
  /** 크기 클래스 (기본: size-4) */
  size?: string;
}

function Spinner({
  variant = 'icon',
  icon: Icon = Loader2,
  size = 'size-4',
  className,
  ...props
}: SpinnerProps) {
  if (variant === 'ring') {
    return (
      <div
        role='status'
        aria-label='Loading'
        className={cn(
          'animate-spin rounded-full border-2 border-current/20 border-t-current',
          size,
          className,
        )}
        {...props}
      />
    );
  }

  return (
    <Icon
      role='status'
      aria-label='Loading'
      className={cn('animate-spin', size, className)}
      {...(props as React.ComponentProps<'svg'>)}
    />
  );
}

export { Spinner };
export type { SpinnerProps, SpinnerVariant };
