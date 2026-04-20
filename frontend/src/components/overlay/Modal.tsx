'use client';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';
import type { ModalOptions } from '@/stores/overlay-store';
import type { ReactNode } from 'react';

const SIZE_CLASSES: Record<NonNullable<ModalOptions['size']>, string> = {
  sm: 'sm:max-w-[400px]',
  md: 'sm:max-w-[520px]',
  lg: 'sm:max-w-[640px]',
  xl: 'sm:max-w-[800px]',
  '2xl': 'sm:max-w-[1024px]',
};

interface ModalProps extends Omit<ModalOptions, 'content'> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = 'md',
  showCloseButton = true,
  stickyFooter = true,
  onClose,
}: ModalProps) {
  const handleOpenChange = (next: boolean) => {
    if (!next) onClose?.();
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        className={cn('flex flex-col gap-0 p-0', SIZE_CLASSES[size])}
        showCloseButton={showCloseButton}
        onPointerDownOutside={(e) => {
          if (
            e.target instanceof Element &&
            e.target.closest('[data-sonner-toast]')
          ) {
            e.preventDefault();
          }
        }}
      >
        {(title || description) && (
          <DialogHeader className='border-line-primary border-b px-6 py-4'>
            {title && (
              <DialogTitle className='text-fg-primary text-base font-semibold'>
                {title}
              </DialogTitle>
            )}
            {description && (
              <DialogDescription className='text-fg-secondary text-sm'>
                {description}
              </DialogDescription>
            )}
          </DialogHeader>
        )}

        {stickyFooter ? (
          <>
            <div className='flex-1 overflow-y-auto px-6 py-5'>{children}</div>
            {footer && (
              <DialogFooter className='border-line-primary border-t px-6 py-4'>
                {footer}
              </DialogFooter>
            )}
          </>
        ) : (
          <div className='flex-1 overflow-y-auto px-6 py-5'>
            {children}
            {footer && (
              <div className='flex flex-col-reverse gap-2 pt-4 sm:flex-row sm:justify-end'>
                {footer}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
