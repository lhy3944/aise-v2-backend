'use client';

import { CitationAwareSpan } from '@/components/chat/CitationAwareSpan';
import { CitationSourcesContext } from '@/components/chat/CitationContext';
import { ExtractedRequirements } from '@/components/chat/ExtractedRequirements';
import { PlanProgress } from '@/components/chat/PlanProgress';
import {
  Questionnaire,
  type QuestionData,
} from '@/components/chat/Questionnaire';
import { SourceReference } from '@/components/chat/SourceReference';
import { SuggestionChips } from '@/components/chat/SuggestionChips';
import {
  Message,
  MessageActions,
  MessageBubble,
  MessageContent,
  MessageResponse,
} from '@/components/ui/ai-elements/message';
import { ToolCall } from '@/components/ui/ai-elements/tool-call';
import { WaveDots } from '@/components/ui/ai-elements/wave-dots';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { createCitationPlugin } from '@/lib/markdown/citation-plugin';
import type { ChatMessage } from '@/stores/chat-store';
import { memo, useMemo } from 'react';
import { Shimmer } from '../ui/ai-elements/shimmer';

interface MessageRendererProps {
  messages: ChatMessage[];
  onSendMessage?: (text: string) => void;
  /** 첫 세션 응답 대기 중일 때 skeleton UI 표시 여부 */
  firstResponseSkeleton?: boolean;
}

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  // record CUD / legacy tool-calling loop
  extract_records: '레코드 추출',
  generate_srs: 'SRS 문서 생성',
  create_record: '레코드 생성',
  update_record: '레코드 수정',
  delete_record: '레코드 삭제',
  update_record_status: '상태 변경',
  search_records: '레코드 검색',
  // LangGraph agent invocations (tool_call.name == agent name)
  knowledge_qa: '지식 검색',
  requirement: '요구사항 추출',
  srs_generator: 'SRS 생성',
  testcase_generator: '테스트케이스 생성',
  critic: '검토',
};

interface RequirementData {
  type: string;
  text: string;
  reason: string;
}

const CLARIFY_BLOCK_RE =
  /```[\w]*\s*\[CLARIFY\]\s*([\s\S]*?)\s*\[\/CLARIFY\]\s*```|\[CLARIFY\]\s*([\s\S]*?)\s*\[\/CLARIFY\]/g;
const REQUIREMENTS_BLOCK_RE =
  /```[\w]*\s*\[REQUIREMENTS\]\s*([\s\S]*?)\s*\[\/REQUIREMENTS\]\s*```|\[REQUIREMENTS\]\s*([\s\S]*?)\s*\[\/REQUIREMENTS\]/g;
const SUGGESTIONS_BLOCK_RE =
  /```[\w]*\s*\[SUGGESTIONS\]\s*([\s\S]*?)\s*\[\/SUGGESTIONS\]\s*```|\[SUGGESTIONS\]\s*([\s\S]*?)\s*\[\/SUGGESTIONS\]/g;

interface ParsedBlocks {
  clarifyItems: QuestionData[];
  requirementItems: RequirementData[];
  suggestions: string[];
  cleanContent: string;
}

function parseStructuredBlocks(content: string): ParsedBlocks {
  const clarifyItems: QuestionData[] = [];
  const requirementItems: RequirementData[] = [];
  const suggestions: string[] = [];
  let cleanContent = content;

  for (const match of content.matchAll(CLARIFY_BLOCK_RE)) {
    const jsonStr = match[1] ?? match[2];
    try {
      const parsed = JSON.parse(jsonStr);
      if (Array.isArray(parsed)) {
        clarifyItems.push(...(parsed as QuestionData[]));
      } else {
        clarifyItems.push(parsed as QuestionData);
      }
    } catch {
      // ignore partial JSON while streaming
    }
    cleanContent = cleanContent.replace(match[0], '');
  }

  for (const match of content.matchAll(REQUIREMENTS_BLOCK_RE)) {
    const jsonStr = match[1] ?? match[2];
    try {
      const parsed = JSON.parse(jsonStr);
      if (Array.isArray(parsed)) {
        requirementItems.push(...(parsed as RequirementData[]));
      }
    } catch {
      // ignore partial JSON while streaming
    }
    cleanContent = cleanContent.replace(match[0], '');
  }

  for (const match of content.matchAll(SUGGESTIONS_BLOCK_RE)) {
    const jsonStr = match[1] ?? match[2];
    try {
      const parsed = JSON.parse(jsonStr);
      if (Array.isArray(parsed)) {
        suggestions.push(...(parsed as string[]));
      }
    } catch {
      // ignore partial JSON while streaming
    }
    cleanContent = cleanContent.replace(match[0], '');
  }

  return {
    clarifyItems,
    requirementItems,
    suggestions,
    cleanContent: cleanContent.trim(),
  };
}

/* ── Message Item ── */

interface MessageItemProps {
  message: ChatMessage;
  isLast: boolean;
  onSendMessage?: (text: string) => void;
  firstResponseSkeleton?: boolean;
}

const MessageItem = memo(
  function MessageItem({
    message,
    isLast,
    onSendMessage,
    firstResponseSkeleton,
  }: MessageItemProps) {
    const isUser = message.role === 'user';
    const showCursor = !isUser && message.status === 'streaming';

    // 스트리밍 중에도 불완전한 구조화 블록을 감지하여 숨기고,
    // 완료 후에는 정식 파싱으로 컴포넌트 렌더링
    const parsed = useMemo(() => {
      if (isUser)
        return {
          clarifyItems: [],
          requirementItems: [],
          suggestions: [],
          cleanContent: message.content,
          hasIncompleteBlock: false,
        };
      if (message.status === 'streaming') {
        // 스트리밍 중: 열린 블록 태그가 있지만 닫는 태그가 없으면 불완전
        const blockTags = ['CLARIFY', 'REQUIREMENTS', 'SUGGESTIONS'];
        let cleanContent = message.content;
        let hasIncompleteBlock = false;

        for (const tag of blockTags) {
          // 완성된 블록은 제거 (JSON이 노출되지 않도록)
          const completeRe = new RegExp(
            `\`\`\`[\\w]*\\s*\\[${tag}\\]\\s*[\\s\\S]*?\\[/${tag}\\]\\s*\`\`\`|\\[${tag}\\]\\s*[\\s\\S]*?\\[/${tag}\\]`,
            'g',
          );
          cleanContent = cleanContent.replace(completeRe, '');

          // 열린 블록이 남아있으면 불완전
          const openRe = new RegExp(`\\[${tag}\\]`);
          if (openRe.test(cleanContent)) {
            hasIncompleteBlock = true;
            // 열린 태그부터 끝까지 제거
            const openIdx = cleanContent.search(openRe);
            cleanContent = cleanContent.slice(0, openIdx);
          }
        }

        return {
          clarifyItems: [],
          requirementItems: [],
          suggestions: [],
          cleanContent: cleanContent.trim(),
          hasIncompleteBlock,
        };
      }
      return {
        ...parseStructuredBlocks(message.content),
        hasIncompleteBlock: false,
      };
    }, [message.content, message.status, isUser]);

    const displayContent = parsed.cleanContent;
    // message.sources가 undefined일 때 매 렌더마다 새 배열이 만들어져
    // 아래 useMemo deps가 흔들리는 것을 방지.
    const sources = useMemo(
      () => message.sources ?? [],
      [message.sources],
    );

    // sources에 존재하는 ref 번호 집합 — rehype 플러그인이 이 집합에
    // 포함된 [N]만 클릭 가능한 span으로 변환.
    const allowedRefs = useMemo(
      () => new Set(sources.map((s) => s.ref)),
      [sources],
    );

    // 답변 텍스트에서 실제 등장한 [N] 번호 집합 —
    // SourceReference가 인용되지 않은 문서를 걸러내는 데 사용.
    const usedRefs = useMemo(() => {
      const out = new Set<number>();
      for (const m of displayContent.matchAll(/\[(\d+)\]/g)) {
        const ref = Number(m[1]);
        if (allowedRefs.has(ref)) out.add(ref);
      }
      return out;
    }, [displayContent, allowedRefs]);

    const rehypePlugins = useMemo(
      () => (allowedRefs.size > 0 ? [createCitationPlugin(allowedRefs)] : undefined),
      [allowedRefs],
    );

    const mdComponents = useMemo(
      () => (allowedRefs.size > 0 ? { span: CitationAwareSpan } : undefined),
      [allowedRefs],
    );

    return (
      <Message from={message.role}>
        <MessageContent from={message.role}>
          {isUser ? (
            <MessageBubble>{message.content}</MessageBubble>
          ) : (
            <>
              {/* 응답 대기 인디케이터 — 토큰/툴콜 어느 것도 아직 도착 전일
                  때만. 툴콜이 먼저 오면 그 카드가 진행 상태를 보여주므로
                  중복 표시를 피한다. 첫 세션의 첫 응답이면 skeleton도 함께. */}
              {showCursor &&
                !message.content &&
                (!message.toolCalls || message.toolCalls.length === 0) && (
                  <>
                    <div className="mb-3 flex items-center gap-2">
                      <Spinner variant="ring" />
                      <Shimmer className="text-sm" duration={1.5} spread={1.5}>
                        응답을 생성하고 있습니다
                      </Shimmer>
                      <WaveDots />
                    </div>
                    {firstResponseSkeleton && (
                      <div className="flex w-full flex-col gap-2">
                        <Skeleton className="h-4 w-[85%]" />
                        <Skeleton className="h-4 w-[70%]" />
                        <Skeleton className="h-4 w-[55%]" />
                      </div>
                    )}
                  </>
                )}

              {/* Plan Progress — supervisor 가 plan 을 결정했을 때만 등장.
                  tool_call 보다 먼저 도착하므로 최상단. */}
              {message.plan && message.plan.length > 0 && (
                <div className='w-full min-w-0'>
                  <PlanProgress
                    plan={message.plan}
                    currentStep={message.currentPlanStep}
                  />
                </div>
              )}

              {/* Tool Calls — SSE 도착 순서상 token보다 먼저 오므로 상단 */}
              {message.toolCalls && message.toolCalls.length > 0 && (
                <div className="w-full min-w-0">
                  {message.toolCalls.map((tc, i) => (
                    <ToolCall
                      key={`${tc.name}-${i}`}
                      name={TOOL_DISPLAY_NAMES[tc.name] ?? tc.name}
                      state={tc.state}
                      input={
                        Object.keys(tc.arguments).length > 0
                          ? tc.arguments
                          : undefined
                      }
                      output={tc.result}
                      error={tc.error}
                      startedAt={tc.startedAt}
                      durationMs={tc.durationMs}
                    />
                  ))}
                </div>
              )}

              {/* 텍스트 응답 (마크다운) — 인라인 출처 클릭 지원.
                  rehype 플러그인이 AST 단계에서 [N]을 span 요소로 치환하므로
                  스트리밍 재렌더에도 링크가 유지된다. 하단 출처 카드는
                  스트리밍 완료 후에만 렌더 → 답변이 먼저 타이핑되고
                  출처 리스트는 뒤따라 나타남. */}
              {displayContent && (
                <div className="w-full min-w-0">
                  <CitationSourcesContext.Provider value={sources}>
                    <MessageResponse
                      streaming={
                        message.status === 'streaming' && !!displayContent
                      }
                      className="w-full"
                      rehypePlugins={rehypePlugins}
                      components={mdComponents}
                    >
                      {displayContent}
                    </MessageResponse>
                  </CitationSourcesContext.Provider>
                </div>
              )}

              {/* 출처 링크 — 스트리밍 완료 후, 본문에 실제 인용된 문서만 표시 */}
              {!showCursor && sources.length > 0 && usedRefs.size > 0 && (
                <div className="w-full min-w-0">
                  <SourceReference sources={sources} usedRefs={usedRefs} />
                </div>
              )}

              {/* REQUIREMENTS 요구사항 카드 */}
              {parsed.requirementItems.length > 0 && (
                <ExtractedRequirements
                  requirements={parsed.requirementItems}
                  onAccept={() => {
                    // TODO: 수락된 요구사항을 레코드 스토어에 반영
                  }}
                />
              )}

              {/* 스트리밍 중 구조화 블록 생성 인디케이터 */}
              {parsed.hasIncompleteBlock && (
                <div className="border-line-primary w-full bg-canvas-surface flex items-center gap-1 rounded-lg border px-4 py-3">
                  <span className="text-fg-muted text-xs">
                    처리중입니다. 잠시만 기다려주세요
                  </span>
                  <WaveDots />
                </div>
              )}

              {/* CLARIFY 질문지 — 마지막 메시지에서만 표시 (제출 후 새 메시지 추가되면 자동 소멸) */}
              {isLast && parsed.clarifyItems.length > 0 && onSendMessage && (
                <Questionnaire
                  questions={parsed.clarifyItems}
                  onSubmit={onSendMessage}
                />
              )}

              {/* SUGGESTIONS 추천 질문 — 마지막 메시지에서만 표시 */}
              {isLast && parsed.suggestions.length > 0 && onSendMessage && (
                <div className="w-full min-w-0">
                  <SuggestionChips
                    suggestions={parsed.suggestions}
                    onSelect={onSendMessage}
                  />
                </div>
              )}

              {/* 액션 (복사 등) — 스트리밍 아닐 때만 */}
              {!showCursor && displayContent && (
                <MessageActions content={displayContent} />
              )}
            </>
          )}
        </MessageContent>
      </Message>
    );
  },
  (prev, next) =>
    prev.message === next.message &&
    prev.isLast === next.isLast &&
    prev.onSendMessage === next.onSendMessage &&
    prev.firstResponseSkeleton === next.firstResponseSkeleton,
);

export const MessageRenderer = memo(function MessageRenderer({
  messages,
  onSendMessage,
  firstResponseSkeleton,
}: MessageRendererProps) {
  if (messages.length === 0) return null;

  const lastIndex = messages.length - 1;

  // 메시지를 턴(user + assistant 세트) 단위로 그룹핑
  const turns: ChatMessage[][] = [];
  for (const msg of messages) {
    if (msg.role === 'user') {
      turns.push([msg]);
    } else if (turns.length > 0) {
      turns[turns.length - 1].push(msg);
    } else {
      turns.push([msg]);
    }
  }

  return (
    <div className="flex flex-col gap-12">
      {turns.map((turn) => (
        <div key={turn[0].id} className="flex flex-col gap-5">
          {turn.map((msg) => {
            const msgIsLast = messages[lastIndex] === msg;
            return (
              <MessageItem
                key={msg.id}
                message={msg}
                isLast={msgIsLast}
                onSendMessage={onSendMessage}
                firstResponseSkeleton={
                  msgIsLast ? firstResponseSkeleton : false
                }
              />
            );
          })}
        </div>
      ))}
    </div>
  );
});
