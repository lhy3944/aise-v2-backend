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
          // close button 을 본문 우상단 안쪽에 고정. toast 자체에 pr 을 줘서
          // title/description 이 close button 영역을 침범하지 않도록 한다.
          closeButton:
            '!right-[-6px] !top-[12px] !left-[unset] !w-6 !w-[24px] !h-[24px] !border-0 !rounded-full',
          toast: '!gap-5 !pr-10',
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
