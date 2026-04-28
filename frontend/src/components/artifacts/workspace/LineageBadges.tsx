'use client';

import { Database, FileText, FlaskConical, Layers } from 'lucide-react';

import { cn } from '@/lib/utils';
import type {
  ArtifactKind,
  SourceArtifactVersionRef,
  SourceArtifactVersions,
} from '@/types/project';

/**
 * "이 산출물 버전이 어떤 입력으로 만들어졌는가" 를 한눈에 보여주는 시각 요소.
 *
 * - 입력은 종류(record/srs/design/testcase)별로 묶어 1개의 칩으로 표시.
 * - 칩의 라벨은 항상 매우 짧게 — 자세한 내역은 hover tooltip 으로.
 * - "기반:" 같은 한국어 산문 대신 좌측 화살표 + 아이콘으로 의미 전달.
 */
interface LineageBadgesProps {
  lineage: SourceArtifactVersions | null | undefined;
  /** artifact_id → display_id 변환. 모르면 fallback. */
  resolveDisplayId?: (artifactId: string) => string | undefined;
  className?: string;
  /** 라벨 prefix 표시 여부 (기본 true). false 면 칩만 표시. */
  showPrefix?: boolean;
}

const KIND_META: Record<
  ArtifactKind,
  { icon: typeof Database; label: string; prefix: string }
> = {
  record: { icon: Database, label: 'Records', prefix: 'REC' },
  srs: { icon: FileText, label: 'SRS', prefix: 'SRS' },
  design: { icon: Layers, label: 'Design', prefix: 'DSG' },
  testcase: { icon: FlaskConical, label: 'TC', prefix: 'TC' },
};

const KIND_ORDER: ArtifactKind[] = ['record', 'srs', 'design', 'testcase'];

export function LineageBadges({
  lineage,
  resolveDisplayId,
  className,
  showPrefix = true,
}: LineageBadgesProps) {
  if (!lineage) return null;

  const groups = KIND_ORDER.map((kind) => ({
    kind,
    entries: (lineage[kind] ?? []) as SourceArtifactVersionRef[],
  })).filter((g) => g.entries.length > 0);

  if (groups.length === 0) return null;

  return (
    <div
      className={cn(
        'text-fg-muted flex flex-wrap items-center gap-1.5 text-[11px]',
        className,
      )}
    >
      {showPrefix && (
        <span className='text-fg-muted/70 inline-flex items-center gap-0.5'>
          <span aria-hidden>←</span>
          <span className='sr-only'>입력</span>
        </span>
      )}
      {groups.map((g) => (
        <LineageChip
          key={g.kind}
          kind={g.kind}
          entries={g.entries}
          resolveDisplayId={resolveDisplayId}
        />
      ))}
    </div>
  );
}

function LineageChip({
  kind,
  entries,
  resolveDisplayId,
}: {
  kind: ArtifactKind;
  entries: SourceArtifactVersionRef[];
  resolveDisplayId?: (artifactId: string) => string | undefined;
}) {
  const meta = KIND_META[kind];
  const Icon = meta.icon;

  // 짧은 라벨: 단일 입력이면 "SRS v1" 형태, 다수면 "Records · 51개" 형태.
  const label = (() => {
    if (entries.length === 1) {
      const e = entries[0];
      const labelText =
        resolveDisplayId?.(e.artifact_id) ??
        `${meta.prefix}-${e.artifact_id.slice(0, 6)}`;
      return e.version_number != null
        ? `${labelText} v${e.version_number}`
        : labelText;
    }
    return `${meta.label} · ${entries.length}개`;
  })();

  // 상세 tooltip: 각 entry 를 한 줄씩.
  const tooltip = entries
    .slice(0, 12)
    .map((e) => {
      const id =
        resolveDisplayId?.(e.artifact_id) ??
        `${meta.prefix}-${e.artifact_id.slice(0, 6)}`;
      const v = e.version_number != null ? `v${e.version_number}` : 'v?';
      const sec = e.section_id ? ` §${e.section_id.slice(0, 6)}` : '';
      return `${id}${sec} ${v}`;
    })
    .join('\n') +
    (entries.length > 12 ? `\n…(+${entries.length - 12})` : '');

  return (
    <span
      className='border-line-primary bg-canvas-surface text-fg-secondary inline-flex max-w-[220px] items-center gap-1 truncate rounded border px-1.5 py-0.5'
      title={tooltip}
    >
      <Icon className='size-3 shrink-0' />
      <span className='truncate'>{label}</span>
    </span>
  );
}
