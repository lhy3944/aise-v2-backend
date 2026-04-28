import type { ArtifactKind } from '@/types/agent-events';
import type { JsonObject } from '@/types/project';

/**
 * staging tray / PR 생성 폼 / diff 헤더에서 보여줄 한 줄 preview 문자열.
 *
 * artifact_type 마다 content payload 구조가 달라 한 줄 요약 규칙이 다르다.
 * 새 artifact_type 추가 시 여기 케이스를 추가하면 모든 staging UI 가 자동 반영된다.
 */
export function previewContent(
  kind: ArtifactKind,
  content: JsonObject,
): string {
  switch (kind) {
    case 'record':
      return asString(content.text);

    case 'srs': {
      const sections = content.sections;
      if (Array.isArray(sections) && sections.length > 0) {
        const titles = sections
          .map((s) => (s && typeof s === 'object' ? asString((s as JsonObject).title) : ''))
          .filter(Boolean);
        if (titles.length > 0) {
          return titles.slice(0, 3).join(' · ') + (titles.length > 3 ? ' …' : '');
        }
      }
      return asString(content.title);
    }

    case 'design': {
      const sections = content.sections;
      if (Array.isArray(sections) && sections.length > 0) {
        const titles = sections
          .map((s) => (s && typeof s === 'object' ? asString((s as JsonObject).title) : ''))
          .filter(Boolean);
        if (titles.length > 0) {
          return titles.slice(0, 3).join(' · ') + (titles.length > 3 ? ' …' : '');
        }
      }
      return asString(content.title);
    }

    case 'testcase':
      return asString(content.title) || asString(content.scenario);
  }
}

function asString(v: unknown): string {
  if (typeof v === 'string') return v;
  if (v == null) return '';
  return String(v);
}
