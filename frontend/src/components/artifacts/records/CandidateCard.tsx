import { ConfidenceIndicator } from '@/components/artifacts/records/RecordCard';
import { cn } from '@/lib/utils';
import type { ArtifactRecordExtractedItem } from '@/types/project';
import { Check } from 'lucide-react';
import { memo } from 'react';

interface CandidateCardProps {
  candidate: ArtifactRecordExtractedItem;
  idx: number;
  selected: boolean;
  onToggle: (idx: number) => void;
}

export const CandidateCard = memo(function CandidateCard({
  candidate,
  idx,
  selected,
  onToggle,
}: CandidateCardProps) {
  return (
    <button
      onClick={() => onToggle(idx)}
      className={cn(
        'group flex items-start gap-3 rounded-lg border px-3.5 py-3 text-left transition-colors',
        selected
          ? 'border-fg-primary/30 bg-canvas-primary/60'
          : 'border-line-primary hover:border-fg-muted/50 hover:bg-canvas-primary/30',
      )}
    >
      <div
        className={cn(
          'mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-[4px] border transition-colors',
          selected
            ? 'border-fg-primary bg-fg-primary text-canvas-primary'
            : 'border-fg-muted/50 group-hover:border-fg-muted',
        )}
      >
        {selected && <Check className='size-3' strokeWidth={3} />}
      </div>
      <div className='min-w-0 flex-1 space-y-1.5'>
        {(candidate.section_name ||
          candidate.confidence_score != null) && (
          <div className='text-fg-muted flex items-center gap-2 text-[11px]'>
            {candidate.section_name && (
              <span className='text-fg-secondary font-medium'>
                {candidate.section_name}
              </span>
            )}
            {candidate.section_name &&
              candidate.confidence_score != null && (
                <span className='opacity-40'>·</span>
              )}
            <ConfidenceIndicator score={candidate.confidence_score} />
          </div>
        )}
        <p className='text-fg-primary text-sm leading-relaxed'>
          {candidate.content}
        </p>
        {candidate.source_document_name && (
          <p className='text-fg-muted truncate text-[11px]'>
            {candidate.source_document_name}
            {candidate.source_location && (
              <span className='opacity-70'>
                {' '}
                · {candidate.source_location}
              </span>
            )}
          </p>
        )}
      </div>
    </button>
  );
});
