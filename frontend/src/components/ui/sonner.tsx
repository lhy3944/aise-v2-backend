'use client';

import { Check, CircleX, InfoIcon, TriangleAlertIcon } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Toaster as Sonner, type ToasterProps } from 'sonner';
import { Spinner } from './spinner';

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = 'system' } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps['theme']}
      closeButton={false}
      className='toaster group pointer-events-auto'
      toastOptions={{
        closeButton: true,
        classNames: {
          closeButton: '!right-[-6px] !left-[unset] !top-4 !w-[30px] !h-[30px] !border-0',
          toast: '!gap-5',
        },
      }}
      icons={{
        success: <Check className='size-7 text-green-500' />,
        info: <InfoIcon className='size-7' />,
        warning: <TriangleAlertIcon className='size-7 text-yellow-500' />,
        error: <CircleX className='size-7 text-red-500' />,
        loading: <Spinner className='size-5' />,
      }}
      style={
        {
          '--normal-bg': 'var(--popover)',
          '--normal-text': 'var(--popover-foreground)',
          '--normal-border': 'var(--border)',
          '--border-radius': 'var(--radius)',
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
