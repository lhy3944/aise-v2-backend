'use client';

import { AlertCircle } from 'lucide-react';

import { cn } from '@/lib/utils';
import type { ImpactedArtifact } from '@/types/project';

interface StaleBadgeProps {
  impact: ImpactedArtifact;
  className?: string;
}

/**
 * "n개 입력 변경됨" 형태의 작은 배지. tooltip 으로 stale_reasons 상세.
 */
export function StaleBadge({ impact, className }: StaleBadgeProps) {
  const count = impact.stale_reasons.length;
  if (count === 0) return null;

  const tooltip = impact.stale_reasons
    .slice(0, 6)
    .map((r) => {
      const label =
        r.source_display_id ??
        `${r.source_artifact_type.toUpperCase()}-${r.source_artifact_id.slice(0, 6)}`;
      const ref = r.referenced_version != null ? `v${r.referenced_version}` : 'v?';
      const cur = r.current_version != null ? `v${r.current_version}` : 'v?';
      const sec = r.section_id ? ` §${r.section_id.slice(0, 6)}` : '';
      return `${label}${sec}: ${ref} → ${cur}`;
    })
    .join('\n') +
    (impact.stale_reasons.length > 6
      ? `\n…(+${impact.stale_reasons.length - 6})`
      : '');

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400',
        className,
      )}
      title={tooltip}
    >
      <AlertCircle className='size-3' />
      stale · {count}
    </span>
  );
}
