'use client';

import { streamAgentChat } from '@/services/agent-service';
import { streamExtractArtifactRecords } from '@/services/artifact-record-service';
import { sessionService } from '@/services/session-service';
import { srsService } from '@/services/srs-service';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { useArtifactStore } from '@/stores/artifact-store';
import type { ChatMessage, ToolCallData } from '@/stores/chat-store';
import { useChatStore } from '@/stores/chat-store';
import type { SourceRef } from '@/types/agent-events';
import { LayoutMode, usePanelStore } from '@/stores/panel-store';
import { useProjectStore } from '@/stores/project-store';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

const EMPTY_MESSAGES: ChatMessage[] = [];

/** 백엔드 도구 결과를 사용자 친화적 문자열로 포맷 */
function formatToolResult(name: string, result: Record<string, unknown>): string {
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
      // sources_count는 검색된 top-k 청크 개수 — "문서"라고 표기하면 오해를 준다
      // (같은 문서의 여러 청크가 여러 번 카운트되므로). 청크 개수로 표기.
      const count = result.sources_count;
      return typeof count === 'number' ? `청크 ${count}개 참조` : '완료';
    }
    case 'requirement': {
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

/**
 * 채팅 메시지 전송, 스트리밍, tool call 실행, 세션 로드를 관리
 */
export function useChatStream(sessionId?: string) {
  const router = useRouter();
  const setRightPanelPreset = usePanelStore((s) => s.setRightPanelPreset);
  const isMobile = usePanelStore((s) => s.isMobile);
  const currentProject = useProjectStore((s) => s.currentProject);
  const [pendingSessionId, setPendingSessionId] = useState<string | undefined>(
    sessionId,
  );
  const activeSessionId = sessionId ?? pendingSessionId;

  const setInputValue = useChatStore((s) => s.setInputValue);
  const addMessage = useChatStore((s) => s.addMessage);
  const appendToLastAssistant = useChatStore((s) => s.appendToLastAssistant);
  const setMessages = useChatStore((s) => s.setMessages);
  const setSessionStreaming = useChatStore((s) => s.setSessionStreaming);
  const finishStreaming = useChatStore((s) => s.finishStreaming);

  const messages = useChatStore(
    (s) =>
      (activeSessionId ? s.sessionMessages[activeSessionId] : undefined) ??
      EMPTY_MESSAGES,
  );
  const isStreaming = useChatStore((s) =>
    activeSessionId ? s.streamingSessionIds.has(activeSessionId) : false,
  );

  const abortControllersRef = useRef<Map<string, () => void>>(new Map());
  const tokenBufferRef = useRef<Map<string, string>>(new Map());
  const tokenDrainTimerRef = useRef<Map<string, number>>(new Map());
  const pendingFinishStatusRef = useRef<Map<string, 'done' | 'error'>>(
    new Map(),
  );
  const [isLoadingMessages, setIsLoadingMessages] = useState<boolean>(
    () =>
      !!activeSessionId &&
      !useChatStore.getState().sessionMessages[activeSessionId],
  );
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // sessionId 변경 시 로딩 상태 동기화
  useEffect(() => {
    if (sessionId) {
      setPendingSessionId(sessionId);
    }
  }, [sessionId]);

  const prevSessionIdRef = useRef(activeSessionId);
  if (prevSessionIdRef.current !== activeSessionId) {
    prevSessionIdRef.current = activeSessionId;
    const needsLoading =
      !!activeSessionId &&
      !useChatStore.getState().sessionMessages[activeSessionId];
    if (needsLoading !== isLoadingMessages) {
      setIsLoadingMessages(needsLoading);
    }
  }

  useEffect(() => {
    if (isLoadingMessages && messages.length > 0) {
      setIsLoadingMessages(false);
    }
  }, [isLoadingMessages, messages.length]);

  // Record store
  const setExtracting = useArtifactRecordStore((s) => s.setExtracting);
  const setCandidates = useArtifactRecordStore((s) => s.setCandidates);
  const setExtractError = useArtifactRecordStore((s) => s.setExtractError);
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);

  // 세션 메시지 로드
  useEffect(() => {
    if (!activeSessionId) return;
    const cached = useChatStore.getState().sessionMessages[activeSessionId];
    if (cached) return;

    let cancelled = false;
    sessionService
      .get(activeSessionId)
      .then((detail) => {
        if (cancelled) return;
        const msgs: ChatMessage[] = detail.messages.map((m) => {
          // backend가 tool_data에 { sources } 등 다양한 보조 데이터를 넣는다.
          // 인용 복원을 위해 sources는 message.sources로 끌어올리고, 그 외
          // 페이로드가 있을 때만 toolData(requirements 스키마)로 래핑한다.
          const td = m.tool_data;
          const sourcesField =
            td && 'sources' in td
              ? (td.sources as SourceRef[] | null | undefined)
              : undefined;
          const tdEntries = td
            ? Object.entries(td).filter(([k]) => k !== 'sources')
            : [];
          const tdRest = Object.fromEntries(tdEntries);
          const hasOtherToolData = tdEntries.length > 0;

          return {
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            toolCalls: m.tool_calls?.map((tc) => {
              const state: 'completed' | 'error' =
                tc.status === 'error' ? 'error' : 'completed';
              const resultText =
                tc.result && typeof tc.result === 'object'
                  ? formatToolResult(
                      tc.name,
                      tc.result as Record<string, unknown>,
                    )
                  : undefined;
              return {
                name: tc.name,
                arguments: tc.arguments,
                state,
                result: state === 'completed' ? resultText : undefined,
                durationMs: tc.duration_ms,
              };
            }),
            toolData: hasOtherToolData
              ? { type: 'requirements' as const, data: tdRest }
              : undefined,
            sources: sourcesField ?? undefined,
            createdAt: m.created_at,
          };
        });
        setMessages(activeSessionId, msgs);
        setIsLoadingMessages(false);
      })
      .catch((err) => {
        // 에러를 조용히 삼키면 empty screen으로 빠지는 현상의 원인 파악이
        // 어렵다. 진단을 위해 콘솔에 남기고 loading 플래그만 해제한다.
        console.error(
          `[useChatStream] session load failed (sessionId=${activeSessionId})`,
          err,
        );
        if (!cancelled) setIsLoadingMessages(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeSessionId, setMessages]);

  // 레코드 추출 실행 (SSE 스트리밍)
  const triggerExtractRecords = useCallback(
    (projectId: string, sid: string) => {
      setExtracting(true);
      setActiveTab('records');
      setRightPanelPreset(LayoutMode.SPLIT);
      const updateLast = useChatStore.getState().updateLastAssistantMessage;

      streamExtractArtifactRecords(projectId, undefined, {
        onDone: (candidates) => {
          setCandidates(candidates);
          updateLast(sid, (msg) => ({
            ...msg,
            toolCalls: msg.toolCalls?.map((tc) =>
              tc.name === 'extract_records'
                ? {
                    ...tc,
                    state: 'completed' as const,
                    result: `${candidates.length}개 후보 추출`,
                  }
                : tc,
            ),
          }));
        },
        onError: (errorMsg) => {
          setExtractError(errorMsg);
          updateLast(sid, (msg) => ({
            ...msg,
            toolCalls: msg.toolCalls?.map((tc) =>
              tc.name === 'extract_records'
                ? { ...tc, state: 'error' as const, error: errorMsg }
                : tc,
            ),
          }));
        },
      });
    },
    [setExtracting, setCandidates, setExtractError, setActiveTab, setRightPanelPreset],
  );

  const triggerGenerateSrs = useCallback(
    (projectId: string, sid: string) => {
      setActiveTab('srs');
      setRightPanelPreset(LayoutMode.SPLIT);
      const updateLast = useChatStore.getState().updateLastAssistantMessage;

      void srsService
        .generate(projectId)
        .then((doc) => {
          updateLast(sid, (msg) => ({
            ...msg,
            toolCalls: msg.toolCalls?.map((tc) =>
              tc.name === 'generate_srs' && tc.state === 'running'
                ? {
                    ...tc,
                    state: 'completed' as const,
                    result:
                      typeof doc.version === 'number'
                        ? `SRS v${doc.version} 생성 완료`
                        : 'SRS 생성 완료',
                  }
                : tc,
            ),
          }));
        })
        .catch((error: unknown) => {
          const message =
            error instanceof Error && error.message
              ? error.message
              : 'SRS 생성에 실패했습니다.';
          updateLast(sid, (msg) => ({
            ...msg,
            toolCalls: msg.toolCalls?.map((tc) =>
              tc.name === 'generate_srs' && tc.state === 'running'
                ? {
                    ...tc,
                    state: 'error' as const,
                    error: message,
                  }
                : tc,
            ),
          }));
        });
    },
    [setActiveTab, setRightPanelPreset],
  );

  const markToolCallError = useCallback(
    (sid: string, name: string, message: string) => {
      const updateLast = useChatStore.getState().updateLastAssistantMessage;
      updateLast(sid, (msg) => ({
        ...msg,
        toolCalls: msg.toolCalls?.map((tc) =>
          tc.name === name && tc.state === 'running'
            ? {
                ...tc,
                state: 'error' as const,
                error: message,
              }
            : tc,
        ),
      }));
    },
    [],
  );

  // Records 갱신 트리거
  const bumpRefresh = useArtifactRecordStore((s) => s.bumpRefresh);

  const clearBufferedTokens = useCallback((sid: string) => {
    tokenBufferRef.current.delete(sid);
    pendingFinishStatusRef.current.delete(sid);
    const timerId = tokenDrainTimerRef.current.get(sid);
    if (timerId !== undefined) {
      clearTimeout(timerId);
      tokenDrainTimerRef.current.delete(sid);
    }
  }, []);

  const scheduleTokenDrain = useCallback(
    (sid: string, immediate = false) => {
      if (tokenDrainTimerRef.current.has(sid)) return;

      const delay = immediate ? 0 : isMobile ? 18 : 10;
      const timerId = window.setTimeout(() => {
        tokenDrainTimerRef.current.delete(sid);

        const buffered = tokenBufferRef.current.get(sid) ?? '';
        if (!buffered) {
          const pendingStatus = pendingFinishStatusRef.current.get(sid);
          if (pendingStatus) {
            pendingFinishStatusRef.current.delete(sid);
            finishStreaming(sid, pendingStatus);
          }
          return;
        }

        const chunkSize = isMobile ? 28 : 120;
        const nextChunk = buffered.slice(0, chunkSize);
        const rest = buffered.slice(chunkSize);

        appendToLastAssistant(sid, nextChunk);

        if (rest) tokenBufferRef.current.set(sid, rest);
        else tokenBufferRef.current.delete(sid);

        if (
          tokenBufferRef.current.has(sid) ||
          pendingFinishStatusRef.current.has(sid)
        ) {
          scheduleTokenDrain(sid);
        }
      }, delay);

      tokenDrainTimerRef.current.set(sid, timerId);
    },
    [appendToLastAssistant, finishStreaming, isMobile],
  );

  const flushBufferedTokens = useCallback(
    (sid: string) => {
      const timerId = tokenDrainTimerRef.current.get(sid);
      if (timerId !== undefined) {
        clearTimeout(timerId);
        tokenDrainTimerRef.current.delete(sid);
      }

      const buffered = tokenBufferRef.current.get(sid);
      if (buffered) {
        appendToLastAssistant(sid, buffered);
      }
      tokenBufferRef.current.delete(sid);

      const pendingStatus = pendingFinishStatusRef.current.get(sid);
      if (pendingStatus) {
        pendingFinishStatusRef.current.delete(sid);
        finishStreaming(sid, pendingStatus);
      }
    },
    [appendToLastAssistant, finishStreaming],
  );

  const enqueueToken = useCallback(
    (sid: string, token: string) => {
      const prev = tokenBufferRef.current.get(sid) ?? '';
      tokenBufferRef.current.set(sid, prev + token);
      scheduleTokenDrain(sid, true);
    },
    [scheduleTokenDrain],
  );

  const requestFinishAfterDrain = useCallback(
    (sid: string, status: 'done' | 'error') => {
      pendingFinishStatusRef.current.set(sid, status);
      scheduleTokenDrain(sid);
    },
    [scheduleTokenDrain],
  );

  // Tool call 실행 디스패처
  const executeToolCall = useCallback(
    (sid: string, name: string, _args: Record<string, unknown>) => {
      if (!currentProject) {
        markToolCallError(
          sid,
          name,
          '프로젝트 정보가 없어 도구를 실행할 수 없습니다.',
        );
        return;
      }
      switch (name) {
        case 'extract_records':
          triggerExtractRecords(currentProject.project_id, sid);
          break;
        case 'generate_srs':
          triggerGenerateSrs(currentProject.project_id, sid);
          break;
      }
    },
    [currentProject, markToolCallError, triggerExtractRecords, triggerGenerateSrs],
  );

  // 백엔드 도구 실행 결과 처리 (레코드 CUD + agent 호출)
  const handleToolResult = useCallback(
    (
      sid: string,
      name: string,
      result: Record<string, unknown>,
      status?: 'success' | 'error',
      durationMs?: number,
    ) => {
      const updateLast = useChatStore.getState().updateLastAssistantMessage;

      // 레코드 CUD 도구 결과 → Records 탭 갱신
      if (['create_record', 'update_record', 'delete_record', 'update_record_status'].includes(name)) {
        bumpRefresh();
      }

      // SSE `tool_result.status`를 우선. legacy agent_svc 결과 모양
      // (`result.success: false`)은 backward-compat를 위해 OR 결합.
      const isError = status === 'error' || result.success === false;
      const newState: 'completed' | 'error' = isError ? 'error' : 'completed';
      updateLast(sid, (msg) => ({
        ...msg,
        toolCalls: msg.toolCalls?.map((tc) =>
          tc.name === name && tc.state === 'running'
            ? {
                ...tc,
                state: newState,
                result: isError ? undefined : formatToolResult(name, result),
                error: isError ? (result.error as string | undefined) : undefined,
                durationMs: durationMs ?? tc.durationMs,
              }
            : tc,
        ),
      }));
    },
    [bumpRefresh],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || !currentProject || isStreaming) return;

      let targetSessionId = activeSessionId;

      // 세션이 없으면 서버에서 생성 → URL 변경
      if (!targetSessionId) {
        setIsCreatingSession(true);
        try {
          const newSession = await sessionService.create(
            currentProject.project_id,
            text.slice(0, 40),
          );
          targetSessionId = newSession.id;
          setPendingSessionId(targetSessionId);
          useChatStore.getState().bumpSessionListNonce();
          router.replace(`/agent/${targetSessionId}`);
          setIsCreatingSession(false);
        } catch {
          setIsCreatingSession(false);
          return;
        }
      }

      // UI에 user 메시지 즉시 추가
      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: text,
        createdAt: new Date().toISOString(),
      };
      addMessage(targetSessionId, userMsg);
      setInputValue('');

      // 빈 assistant 메시지 추가 (스트리밍용)
      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: '',
        status: 'streaming',
        createdAt: new Date().toISOString(),
      };
      addMessage(targetSessionId, assistantMsg);
      setSessionStreaming(targetSessionId, true);
      clearBufferedTokens(targetSessionId);

      const updateLastAssistant = useChatStore.getState().updateLastAssistantMessage;

      const abort = streamAgentChat(
        {
          session_id: targetSessionId,
          message: text,
        },
        {
          onToken: (token) => {
            enqueueToken(targetSessionId, token);
          },
          onToolCall: (toolCall) => {
            const tc: ToolCallData = {
              name: toolCall.name,
              arguments: toolCall.arguments,
              state: 'running',
              startedAt: Date.now(),
            };
            updateLastAssistant(targetSessionId, (msg) => ({
              ...msg,
              toolCalls: [...(msg.toolCalls ?? []), tc],
            }));
            executeToolCall(targetSessionId, toolCall.name, toolCall.arguments);
          },
          onToolResult: (toolResult) => {
            handleToolResult(
              targetSessionId,
              toolResult.name,
              toolResult.result,
              toolResult.status,
              toolResult.durationMs,
            );
          },
          onSources: (sources) => {
            updateLastAssistant(targetSessionId, (msg) => ({
              ...msg,
              sources,
            }));
          },
          onPlanUpdate: ({ plan, current_step }) => {
            updateLastAssistant(targetSessionId, (msg) => ({
              ...msg,
              plan,
              currentPlanStep: current_step,
            }));
          },
          onDone: () => {
            requestFinishAfterDrain(targetSessionId, 'done');
          },
          onError: (error) => {
            enqueueToken(targetSessionId, `\n\n⚠️ ${error}`);
            requestFinishAfterDrain(targetSessionId, 'error');
          },
        },
      );

      abortControllersRef.current.set(targetSessionId, abort);
    },
    [
      currentProject,
      activeSessionId,
      isStreaming,
      addMessage,
      setInputValue,
      setSessionStreaming,
      enqueueToken,
      requestFinishAfterDrain,
      executeToolCall,
      handleToolResult,
      router,
    ],
  );

  // 스트리밍 중지
  const stopStreaming = useCallback(() => {
    if (!activeSessionId) return;
    flushBufferedTokens(activeSessionId);
    abortControllersRef.current.get(activeSessionId)?.();
    abortControllersRef.current.delete(activeSessionId);
    finishStreaming(activeSessionId);
  }, [activeSessionId, finishStreaming, flushBufferedTokens]);

  // Cleanup on unmount
  useEffect(() => {
    const controllers = abortControllersRef.current;
    return () => {
      // `/agent` -> `/agent/[sessionId]` route handoff 중에는
      // 기존 스트림을 유지해야 하므로 실제 route param 기준으로만 정리한다.
      if (sessionId) {
        flushBufferedTokens(sessionId);
        controllers.get(sessionId)?.();
        controllers.delete(sessionId);
      }
    };
  }, [sessionId, flushBufferedTokens]);

  return {
    messages,
    isStreaming,
    isLoadingMessages,
    isCreatingSession,
    sendMessage,
    stopStreaming,
    setInputValue,
  };
}
