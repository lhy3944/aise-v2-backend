import type { SourceArtifactVersions } from '@/types/project';

/**
 * lineage 를 selectbox/카드 안에 들어갈 매우 짧은 한 줄로 요약.
 * UUID prefix 같은 노이즈 없이, kind 별 카운트 또는 단일 입력의 version 만 노출.
 *
 * 예)
 *  - SRS 가 record 51 + SRS 0 → "← REC 51"
 *  - DESIGN 이 SRS v3 단독    → "← SRS v3"
 *  - TC 가 SRS v3 단독        → "← SRS v3"
 */
export function lineageInline(
  lineage: SourceArtifactVersions | null | undefined,
): string | null {
  if (!lineage) return null;
  const parts: string[] = [];

  const pushKindCount = (
    label: string,
    entries: { version_number?: number }[] | undefined,
  ) => {
    if (!entries || entries.length === 0) return;
    if (entries.length === 1 && entries[0].version_number != null) {
      parts.push(`${label} v${entries[0].version_number}`);
    } else {
      parts.push(`${label} ${entries.length}`);
    }
  };

  pushKindCount('REC', lineage.record);
  pushKindCount('SRS', lineage.srs);
  pushKindCount('DSG', lineage.design);
  pushKindCount('TC', lineage.testcase);

  return parts.length > 0 ? parts.join(' · ') : null;
}

/**
 * lineage 객체를 짧은 사람이 읽기 쉬운 한 줄로 요약.
 *
 * 예) "기반: REC-003 v2 · REC-005 v1 + SRS v3 §3.2"
 *
 * @param resolveDisplayId - artifact_id → display_id 변환. 모르면 fallback.
 */
export function summarizeLineage(
  lineage: SourceArtifactVersions | null | undefined,
  resolveDisplayId?: (artifactId: string) => string | undefined,
  maxPerKind = 3,
): string {
  if (!lineage) return '';
  const parts: string[] = [];

  const kindOrder: Array<keyof SourceArtifactVersions> = [
    'record',
    'srs',
    'design',
    'testcase',
  ];
  const kindPrefix: Record<keyof SourceArtifactVersions, string> = {
    record: 'REC',
    srs: 'SRS',
    design: 'DSG',
    testcase: 'TC',
  };

  for (const kind of kindOrder) {
    const entries = lineage[kind];
    if (!entries || entries.length === 0) continue;

    const items = entries.slice(0, maxPerKind).map((e) => {
      const label =
        resolveDisplayId?.(e.artifact_id) ??
        `${kindPrefix[kind]}-${e.artifact_id.slice(0, 6)}`;
      const versionPart =
        typeof e.version_number === 'number' ? ` v${e.version_number}` : '';
      const sectionPart = e.section_id ? ` §${e.section_id.slice(0, 6)}` : '';
      return `${label}${versionPart}${sectionPart}`;
    });
    const more =
      entries.length > maxPerKind ? ` (+${entries.length - maxPerKind})` : '';
    parts.push(items.join(' · ') + more);
  }

  return parts.join(' + ');
}
