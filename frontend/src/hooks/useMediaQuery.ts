'use client';

import { useEffect } from 'react';
import { usePanelStore } from '@/stores/panel-store';

export function useResponsivePanel() {
  const setViewport = usePanelStore((s) => s.setViewport);

  useEffect(() => {
    const handleResize = () => setViewport(window.innerWidth);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [setViewport]);
}
