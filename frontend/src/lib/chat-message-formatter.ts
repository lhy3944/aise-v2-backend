import type { ChatMessage, ToolCallData } from '@/stores/chat-store';
import type { HitlData, SourceRef } from '@/types/agent-events';

/** 백엔드 도구 결과를 사용자 친화적 문자열로 포맷 */
export function formatToolResult(
  name: string,
  result: Record<string, unknown>,
): string {
  switch (name) {
    case 'create_record':
      return `${result.display_id} 생성 완료`;
    case 'update_record':
      return `${result.display_id} 수정 완료`;
    case 'delete_record':
      return `${result.display_id} 삭제 완료`;
    case 'update_record_status':
      return `${result.display_id}: ${result.old_status} → ${result.new_status}`;
    case 'search_records':
      return `${result.count}개 레코드 검색됨`;
    case 'generate_srs':
      return typeof result.version === 'number'
        ? `SRS v${result.version} 생성 완료`
        : 'SRS 생성 완료';
    case 'knowledge_qa': {
      const count = result.sources_count;
      return typeof count === 'number' ? `청크 ${count}개 참조` : '완료';
    }
    case 'requirement': {
      const approved = result.records_approved_count;
      if (typeof approved === 'number') {
        return `승인 ${approved}건`;
      }
      const count = result.records_count;
      return typeof count === 'number' ? `후보 ${count}건 추출` : '완료';
    }
    case 'srs_generator': {
      const v = result.srs_version;
      const sections = result.section_count;
      if (typeof v === 'number' && typeof sections === 'number') {
        return `SRS v${v} · ${sections}개 섹션`;
      }
      return typeof v === 'number' ? `SRS v${v} 생성` : 'SRS 생성 완료';
    }
    case 'design_generator': {
      const v = result.design_version;
      const sections = result.section_count;
      const srsVersion = result.srs_version;
      if (
        typeof v === 'number' &&
        typeof sections === 'number' &&
        typeof srsVersion === 'number'
      ) {
        return `Design v${v} · ${sections}개 섹션 · SRS v${srsVersion}`;
      }
      if (typeof v === 'number' && typeof sections === 'number') {
        return `Design v${v} · ${sections}개 섹션`;
      }
      return typeof v === 'number' ? `Design v${v} 생성` : 'Design 생성 완료';
    }
    case 'testcase_generator': {
      const count = result.testcase_count;
      const v = result.srs_version;
      if (typeof count === 'number' && typeof v === 'number') {
        return `TC ${count}건 · SRS v${v}`;
      }
      return typeof count === 'number' ? `TC ${count}건 생성` : 'TC 생성 완료';
    }
    case 'critic': {
      const passed = result.critic_passed;
      const checked = result.checked_citations;
      if (typeof checked === 'number') {
        const status = passed === false ? '실패' : '통과';
        return `검증 ${status} · 인용 ${checked}건`;
      }
      return passed === false ? '검증 실패' : '검증 통과';
    }
    default:
      return '완료';
  }
}

export function formatToolInterrupt(name: string, data: HitlData): string {
  if (name === 'requirement' && data.kind === 'confirm') {
    const records = data.context?.records_extracted;
    if (Array.isArray(records)) {
      return `후보 ${records.length}건 승인 대기`;
    }
  }
  return '사용자 확인 대기';
}

export interface BackendMessage {
  id: string;
  role: string;
  content: string;
  tool_calls?: {
    name: string;
    arguments: Record<string, unknown>;
    status?: string;
    result?: Record<string, unknown> | null;
    duration_ms?: number;
  }[] | null;
  tool_data?: Record<string, unknown> | null;
  created_at: string;
}

/** 백엔드 세션 메시지를 ChatMessage[] 로 변환 */
export function mapBackendMessages(messages: BackendMessage[]): ChatMessage[] {
  return messages.map((m) => {
    const td = m.tool_data;
    const sourcesField =
      td && 'sources' in td
        ? (td.sources as SourceRef[] | null | undefined)
        : undefined;
    const hitlDataField =
      td && 'hitl_data' in td && td.hitl_data != null
        ? (td.hitl_data as HitlData)
        : undefined;
    const tdEntries = td
      ? Object.entries(td).filter(([k]) => k !== 'sources' && k !== 'hitl_data')
      : [];
    const tdRest = Object.fromEntries(tdEntries);
    const hasOtherToolData = tdEntries.length > 0;

    const hitlMeta = hitlDataField
      ? (hitlDataField as unknown as Record<string, unknown>)
      : null;
    const hitlResponded =
      hitlMeta != null ? hitlMeta.responded === true : undefined;
    const hitlApproved =
      hitlMeta != null ? (hitlMeta.approved as boolean | null) : undefined;

    return {
      id: m.id,
      role: m.role as 'user' | 'assistant',
      content: m.content,
      toolCalls: m.tool_calls?.map((tc) => {
        const state: 'completed' | 'error' =
          tc.status === 'error' ? 'error' : 'completed';
        const resultText =
          tc.result && typeof tc.result === 'object'
            ? formatToolResult(tc.name, tc.result as Record<string, unknown>)
            : undefined;
        return {
          name: tc.name,
          arguments: tc.arguments,
          state,
          result: state === 'completed' ? resultText : undefined,
          durationMs: tc.duration_ms,
        } satisfies ToolCallData;
      }),
      toolData: hasOtherToolData
        ? { type: 'requirements' as const, data: tdRest }
        : undefined,
      sources: sourcesField ?? undefined,
      hitlData: hitlDataField,
      hitlResponded,
      hitlApproved,
      hitlArtifactDone: hitlResponded ? true : undefined,
      createdAt: m.created_at,
    };
  });
}
