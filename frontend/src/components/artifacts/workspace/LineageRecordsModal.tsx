'use client';

import { Database } from 'lucide-react';

import { ScrollArea } from '@/components/ui/scroll-area';
import type { SourceArtifactVersionRef } from '@/types/project';

interface LineageRecordsModalProps {
  /** lineage 의 record 배열. */
  records: SourceArtifactVersionRef[];
  /** artifact_id → display_id 매핑. 모르면 fallback. */
  resolveDisplayId?: (artifactId: string) => string | undefined;
  /** 산출물 컨텍스트 — 헤더 부제로 표시 (예: "SRS v3 의 입력 레코드"). */
  contextLabel?: string;
}

/**
 * lineage 에 들어 있는 record 입력 목록을 보여주는 모달 본문.
 *
 * overlay.modal 의 content 로 사용:
 *   overlay.modal({ title: '입력 레코드', content: <LineageRecordsModal ... /> })
 */
export function LineageRecordsModal({
  records,
  resolveDisplayId,
  contextLabel,
}: LineageRecordsModalProps) {
  return (
    <div className='flex h-full min-h-0 flex-col gap-3'>
      <div className='text-fg-muted flex items-center gap-1.5 text-xs'>
        <Database className='size-3.5' />
        <span>총 {records.length}개</span>
        {contextLabel && (
          <>
            <span className='opacity-40'>·</span>
            <span>{contextLabel}</span>
          </>
        )}
      </div>

      <ScrollArea className='border-line-primary min-h-0 flex-1 rounded-md border'>
        <ul className='divide-line-primary divide-y'>
          {records.map((r, idx) => {
            const id =
              resolveDisplayId?.(r.artifact_id) ??
              `REC-${r.artifact_id.slice(0, 6)}`;
            return (
              <li
                key={`${r.artifact_id}-${idx}`}
                className='hover:bg-canvas-primary/40 flex items-center gap-3 px-3 py-2 text-xs'
              >
                <span className='text-fg-muted w-8 shrink-0 text-right font-mono tabular-nums'>
                  {idx + 1}
                </span>
                <span className='text-fg-primary font-mono font-medium'>
                  {id}
                </span>
                <span className='text-fg-muted ml-auto font-mono tabular-nums'>
                  {r.version_number != null ? `v${r.version_number}` : 'v-'}
                </span>
              </li>
            );
          })}
        </ul>
      </ScrollArea>
    </div>
  );
}
