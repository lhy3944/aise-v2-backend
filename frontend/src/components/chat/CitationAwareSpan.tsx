'use client';

import type { HTMLAttributes, MouseEvent } from 'react';
import { useCallback } from 'react';
import { useCitationSources } from '@/components/chat/CitationContext';
import { usePanelStore } from '@/stores/panel-store';

type Props = HTMLAttributes<HTMLSpanElement> & {
  'data-citation-ref'?: string;
};

export function CitationAwareSpan(props: Props) {
  const refAttr = props['data-citation-ref'];
  const sources = useCitationSources();
  const openSourceViewer = usePanelStore((s) => s.openSourceViewer);

  const handleClick = useCallback(
    (e: MouseEvent<HTMLSpanElement>) => {
      if (!refAttr) return;
      const refNum = Number(refAttr);
      const source = sources.find((s) => s.ref === refNum);
      if (!source) return;
      e.stopPropagation();
      openSourceViewer({
        documentId: source.document_id,
        documentName: source.document_name,
        chunkIndex: source.chunk_index,
        refNumber: source.ref,
        fileType: source.file_type,
      });
    },
    [refAttr, sources, openSourceViewer],
  );

  if (!refAttr) {
    return <span {...props} />;
  }

  return (
    <span
      {...props}
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick(e as unknown as MouseEvent<HTMLSpanElement>);
        }
      }}
    />
  );
}
