'use client';

import { createContext, useContext } from 'react';
import type { SourceData } from '@/components/chat/SourceReference';

export const CitationSourcesContext = createContext<SourceData[]>([]);

export function useCitationSources(): SourceData[] {
  return useContext(CitationSourcesContext);
}
