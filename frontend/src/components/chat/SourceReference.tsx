'use client';

import { cn } from '@/lib/utils';
import { usePanelStore } from '@/stores/panel-store';
import { FileText } from 'lucide-react';
import { useMemo } from 'react';

export interface SourceData {
  ref: number;
  document_id: string;
  document_name: string;
  chunk_index: number;
  file_type?: string;
}

interface SourceReferenceProps {
  sources: SourceData[];
  /** 답변 본문에 실제 등장한 인용 번호 집합. 주어지면 이 번호들을 가진 source만 노출. */
  usedRefs?: Set<number>;
}

interface DocumentGroup {
  documentId: string;
  documentName: string;
  /** 칩 정렬용 — 그룹 내 최소 ref (= 본문에 가장 먼저 인용된 청크). */
  minRef: number;
}

/**
 * 출처 칩은 "어떤 문서가 인용됐는지"만 보여주는 **정보 표시 전용** 영역이다.
 * 청크 이동(링크)은 본문의 인라인 [n] 마커가 담당한다 — 같은 문서에서 여러
 * 청크가 인용된 경우, 각 청크는 해당 번호의 인라인 링크로만 접근 가능.
 * `isActive`는 현재 패널에 열린 문서와의 매칭을 시각적으로만 표시한다.
 */
export function SourceReference({ sources, usedRefs }: SourceReferenceProps) {
  const sourceViewerData = usePanelStore((s) => s.sourceViewerData);

  const groups = useMemo<DocumentGroup[]>(() => {
    const filtered = usedRefs
      ? sources.filter((s) => usedRefs.has(s.ref))
      : sources;

    const byDoc = new Map<string, DocumentGroup>();
    for (const s of filtered) {
      const existing = byDoc.get(s.document_id);
      if (existing) {
        if (s.ref < existing.minRef) existing.minRef = s.ref;
      } else {
        byDoc.set(s.document_id, {
          documentId: s.document_id,
          documentName: s.document_name,
          minRef: s.ref,
        });
      }
    }
    // 본문 인용 순서에 맞춰 대표 ref 오름차순.
    return [...byDoc.values()].sort((a, b) => a.minRef - b.minRef);
  }, [sources, usedRefs]);

  if (groups.length === 0) return null;

  return (
    <div className='@container mt-2 space-y-1.5'>
      <span className='text-fg-muted text-xs'>출처</span>
      <div className='@md:grid-cols-2 grid grid-cols-1 gap-1.5'>
        {groups.map((g) => {
          const isActive = sourceViewerData?.documentId === g.documentId;

          return (
            <div
              key={g.documentId}
              className={cn(
                'border-line-primary text-fg-secondary',
                'flex w-full min-w-0 items-center gap-1 rounded-md border p-2 text-xs',
                isActive && 'border-accent-primary text-fg-primary',
              )}
            >
              <FileText className='size-3.5 shrink-0' />
              <span className='min-w-0 flex-1 truncate text-left'>
                {g.documentName}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
