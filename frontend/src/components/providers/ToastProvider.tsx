'use client';

import { AlertCircle, CheckCircle2, Info, X, AlertTriangle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { useToastStore, type ToastItem, type ToastType } from '@/stores/toast-store';

const ICON_MAP: Record<ToastType, React.ElementType> = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
};

const STYLE_MAP: Record<ToastType, string> = {
  success: 'text-emerald-500',
  error: 'text-destructive',
  warning: 'text-amber-500',
  info: 'text-accent-primary',
};

function ToastCard({ toast }: { toast: ToastItem }) {
  const remove = useToastStore((s) => s.remove);
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setExiting(true);
      setTimeout(() => remove(toast.id), 200);
    }, toast.duration);

    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, remove]);

  function handleClose() {
    setExiting(true);
    setTimeout(() => remove(toast.id), 200);
  }

  const Icon = ICON_MAP[toast.type];
  const iconColor = STYLE_MAP[toast.type];

  return (
    <div
      className={cn(
        'border-line-primary bg-popover relative w-80 overflow-hidden rounded-xl border shadow-lg transition-all duration-200',
        exiting ? 'translate-x-full opacity-0' : 'translate-x-0 opacity-100',
      )}
    >
      <div className='flex items-start gap-3 p-4 pr-10'>
        <Icon className={cn('mt-0.5 size-[18px] shrink-0', iconColor)} />
        <div className='min-w-0 flex-1'>
          <p className='text-fg-primary text-sm font-medium'>{toast.message}</p>
          {toast.description && <p className='text-fg-muted mt-0.5 text-xs'>{toast.description}</p>}
        </div>
      </div>

      <button
        onClick={handleClose}
        className='text-fg-muted hover:text-fg-primary absolute top-3 right-3 rounded-md p-0.5 transition-colors'
      >
        <X className='size-3.5' />
      </button>

    </div>
  );
}

export function ToastProvider() {
  const toasts = useToastStore((s) => s.toasts);

  if (toasts.length === 0) return null;

  return (
    <div className='fixed right-4 bottom-4 z-[9999] flex flex-col gap-2'>
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} />
      ))}
    </div>
  );
}
