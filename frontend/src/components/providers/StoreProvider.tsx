'use client';

import { useStoreHydration } from '@/hooks/useStoreHydration';
import { installClipboardPolyfill } from '@/lib/clipboard-polyfill';
import { usePanelStore } from '@/stores/panel-store';

installClipboardPolyfill();

function LoadingScreen() {
  return (
    <div className='bg-canvas-primary flex h-screen w-full items-center justify-center'>
      <div className='flex flex-col items-center gap-4'>
        <div className='relative flex items-center'>
          <span className='text-fg-primary text-3xl font-bold'>AISE</span>
          <span className='text-fg-primary absolute -top-1.5 -right-4 text-xl font-bold'>+</span>
        </div>
        <div className='bg-line-primary h-1 w-24 overflow-hidden rounded-full'>
          <div className='animate-shimmer bg-fg-muted h-full w-1/2 rounded-full' />
        </div>
      </div>
    </div>
  );
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const hydrated = useStoreHydration(usePanelStore);

  if (!hydrated) {
    return <LoadingScreen />;
  }

  return <>{children}</>;
}
