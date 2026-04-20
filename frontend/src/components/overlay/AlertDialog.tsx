'use client';

import { CircleAlert, CircleCheck, CircleX, Info } from 'lucide-react';
import {
  AlertDialog as AlertDialogRoot,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import type { AlertOptions } from '@/stores/overlay-store';

type AlertType = NonNullable<AlertOptions['type']>;

const ALERT_CONFIG: Record<
  AlertType,
  { icon: typeof CircleCheck; iconClass: string; bgClass: string }
> = {
  success: {
    icon: CircleCheck,
    iconClass: 'text-accent-primary',
    bgClass: 'bg-accent-primary/10',
  },
  warning: {
    icon: CircleAlert,
    iconClass: 'text-amber-500',
    bgClass: 'bg-amber-500/10',
  },
  info: {
    icon: Info,
    iconClass: 'text-blue-500',
    bgClass: 'bg-blue-500/10',
  },
  error: {
    icon: CircleX,
    iconClass: 'text-destructive',
    bgClass: 'bg-destructive/10',
  },
};

interface AlertDialogProps extends AlertOptions {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AlertDialog({
  open,
  onOpenChange,
  type = 'info',
  title,
  description,
  confirmLabel = '확인',
  onClose,
}: AlertDialogProps) {
  const { icon: Icon, iconClass, bgClass } = ALERT_CONFIG[type];

  const handleClose = () => {
    onClose?.();
    onOpenChange(false);
  };

  return (
    <AlertDialogRoot open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent size='default' className='gap-0 p-6'>
        <AlertDialogHeader className='flex flex-col items-center gap-4 text-center'>
          <AlertDialogMedia className={`size-14 rounded-full sm:size-10 ${bgClass}`}>
            <Icon className={`size-7 sm:size-5 ${iconClass}`} />
          </AlertDialogMedia>
          <div className='space-y-1.5'>
            <AlertDialogTitle className='text-fg-primary text-base font-semibold'>
              {title}
            </AlertDialogTitle>
            {description && (
              <AlertDialogDescription className='text-primary text-sm'>
                {description}
              </AlertDialogDescription>
            )}
          </div>
        </AlertDialogHeader>
        <AlertDialogFooter className='mt-6 grid-cols-1 justify-center sm:justify-end'>
          <AlertDialogAction onClick={handleClose}>{confirmLabel}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialogRoot>
  );
}
