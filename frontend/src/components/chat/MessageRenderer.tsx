'use client';

import { ExtractedRequirements } from '@/components/chat/ExtractedRequirements';
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
import type { ChatMessage } from '@/stores/chat-store';
import { usePanelStore } from '@/stores/panel-store';
import { memo, useCallback, useEffect, useMemo, useRef } from 'react';
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
    const sources = message.sources ?? [];

    const openSourceViewer = usePanelStore((s) => s.openSourceViewer);
    const contentRef = useRef<HTMLDivElement>(null);

    // 렌더 후 DOM에서 [N] 텍스트를 클릭 가능한 span으로 래핑
    useEffect(() => {
      const el = contentRef.current;
      if (!el || sources.length === 0) return;

      const sourceMap = new Map(sources.map((s) => [s.ref, s]));

      // 이전 래핑 복원 (멱등성 보장)
      el.querySelectorAll('.citation-inline').forEach((span) => {
        span.replaceWith(document.createTextNode(span.textContent || ''));
      });
      el.normalize();

      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const nodes: Text[] = [];
      let n: Node | null;
      while ((n = walker.nextNode())) {
        if (/\[\d+\]/.test(n.textContent || '')) {
          if ((n as Text).parentElement?.closest('pre, code')) continue;
          nodes.push(n as Text);
        }
      }

      for (const textNode of nodes) {
        const text = textNode.textContent || '';
        const frag = document.createDocumentFragment();
        let lastIdx = 0;
        let hasMatch = false;

        for (const m of text.matchAll(/\[(\d+)\]/g)) {
          const ref = parseInt(m[1]);
          if (!sourceMap.has(ref)) continue;
          hasMatch = true;
          if (m.index > lastIdx) {
            frag.appendChild(
              document.createTextNode(text.slice(lastIdx, m.index)),
            );
          }
          const span = document.createElement('span');
          span.textContent = m[0];
          span.className = 'citation-inline';
          span.dataset.citationRef = String(ref);
          frag.appendChild(span);
          lastIdx = m.index + m[0].length;
        }

        if (!hasMatch) continue;
        if (lastIdx < text.length) {
          frag.appendChild(document.createTextNode(text.slice(lastIdx)));
        }
        textNode.parentNode?.replaceChild(frag, textNode);
      }
    }, [displayContent, sources]);

    const handleCitationClick = useCallback(
      (e: React.MouseEvent) => {
        const span = (e.target as HTMLElement).closest<HTMLElement>(
          '[data-citation-ref]',
        );
        if (!span) return;
        const refNum = parseInt(span.dataset.citationRef || '');
        const source = sources.find((s) => s.ref === refNum);
        if (source) {
          openSourceViewer({
            documentId: source.document_id,
            documentName: source.document_name,
            chunkIndex: source.chunk_index,
            refNumber: source.ref,
            fileType: source.file_type,
          });
        }
      },
      [sources, openSourceViewer],
    );

    return (
      <Message from={message.role}>
        <MessageContent from={message.role}>
          {isUser ? (
            <MessageBubble>{message.content}</MessageBubble>
          ) : (
            <>
              {/* 스트림 응답 대기 중 shimmer */}
              {showCursor && !message.content && (
                <div className="mb-3 flex items-center gap-2">
                  <Spinner variant="ring" />
                  <Shimmer className="text-sm" duration={1.5} spread={1.5}>
                    응답을 생성하고 있습니다
                  </Shimmer>
                  <WaveDots />
                </div>
              )}

              {/* 첫 세션 응답 대기 중 skeleton — 첫 메시지 도착 전까지 */}
              {showCursor && !message.content && firstResponseSkeleton && (
                <div className="flex w-full flex-col gap-2">
                  <Skeleton className="h-4 w-[85%]" />
                  <Skeleton className="h-4 w-[70%]" />
                  <Skeleton className="h-4 w-[55%]" />
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
                  sources 데이터는 스트리밍 중에도 message.sources에 세팅돼
                  있어 [N] 클릭 wiring은 즉시 동작. 아래 SourceReference
                  카드는 스트리밍 완료 후에만 렌더 → 답변이 먼저 타이핑되고
                  출처 리스트는 뒤따라 나타남. */}
              {displayContent && (
                <div
                  ref={contentRef}
                  className="w-full min-w-0"
                  onClick={sources.length > 0 ? handleCitationClick : undefined}
                >
                  <MessageResponse
                    streaming={
                      message.status === 'streaming' && !!displayContent
                    }
                    className="w-full"
                  >
                    {displayContent}
                  </MessageResponse>
                </div>
              )}

              {/* 출처 링크 — 스트리밍 완료 후에만 렌더 */}
              {!showCursor && sources.length > 0 && (
                <div className="w-full min-w-0">
                  <SourceReference sources={sources} />
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
