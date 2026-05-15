'use client';

import {
  streamAgentChat,
  streamAgentResume,
  uploadAgentAttachments,
  type AgentAttachmentPayload,
  type StreamCallbacks,
} from '@/services/agent-service';
import { streamExtractArtifactRecords } from '@/services/artifact-record-service';
import { sessionService } from '@/services/session-service';
import { srsService } from '@/services/srs-service';
import {
  formatToolInterrupt,
  formatToolResult,
  mapBackendMessages,
} from '@/lib/chat-message-formatter';
import { useArtifactActionStore } from '@/stores/artifact-action-store';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { useArtifactStore, type ArtifactType } from '@/stores/artifact-store';
import type { ChatMessage, ToolCallData } from '@/stores/chat-store';
import { useChatStore } from '@/stores/chat-store';
import { useHitlStore } from '@/stores/hitl-store';
import type { ArtifactKind, HitlData } from '@/types/agent-events';
import { LayoutMode, usePanelStore } from '@/stores/panel-store';
import { useProjectStore } from '@/stores/project-store';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTokenDrain } from '@/hooks/useTokenDrain';
import type { FileUIPart } from 'ai';

const EMPTY_MESSAGES: ChatMessage[] = [];
const streamAbortControllers = new Map<string, () => void>();

type SendMessageInput = string | { text: string; files?: FileUIPart[] };

function normalizeSendInput(input: SendMessageInput): {
  text: string;
  files: FileUIPart[];
} {
  if (typeof input === 'string') {
    return { text: input, files: [] };
  }
  return { text: input.text, files: input.files ?? [] };
}

async function filePartToFile(file: FileUIPart): Promise<File | null> {
  if (file.type !== 'file' || !file.url) return null;
  const response = await fetch(file.url);
  const blob = await response.blob();
  const name = file.filename ?? 'attachment';
  return new File([blob], name, {
    type: file.mediaType ?? blob.type ?? 'application/octet-stream',
  });
}

function toChatAttachments(attachments: AgentAttachmentPayload[]) {
  return attachments.map((item) => ({
    id: item.id,
    filename: item.filename,
    contentType: item.content_type,
    sizeBytes: item.size_bytes,
    storageKey: item.storage_key,
    textPreview: item.text_preview,
  }));
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

  const pendingHitl = useHitlStore((s) => {
    const active = s.activeThreadId
      ? s.pendingByThreadId[s.activeThreadId]
      : null;
    return active?.sessionId === activeSessionId ? active : null;
  });
  const upsertHitl = useHitlStore((s) => s.upsert);
  const removeHitl = useHitlStore((s) => s.remove);

  const [isLoadingMessages, setIsLoadingMessages] = useState<boolean>(
    () =>
      !!activeSessionId &&
      !useChatStore.getState().sessionMessages[activeSessionId],
  );
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  // Token drain subsystem
  const {
    clearBufferedTokens,
    flushBufferedTokens,
    enqueueToken,
    requestFinishAfterDrain,
  } = useTokenDrain({ isMobile });

  // sessionId 변경 시 로딩 상태 동기화
  useEffect(() => {
    if (sessionId) {
      queueMicrotask(() => setPendingSessionId(sessionId));
    }
  }, [sessionId]);

  const prevSessionIdRef = useRef(activeSessionId);
  useEffect(() => {
    if (prevSessionIdRef.current !== activeSessionId) {
      prevSessionIdRef.current = activeSessionId;
      const needsLoading =
        !!activeSessionId &&
        !useChatStore.getState().sessionMessages[activeSessionId];
      if (needsLoading !== isLoadingMessages) {
        queueMicrotask(() => setIsLoadingMessages(needsLoading));
      }
    }
  }, [activeSessionId, isLoadingMessages]);

  useEffect(() => {
    if (isLoadingMessages && messages.length > 0) {
      queueMicrotask(() => setIsLoadingMessages(false));
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
        const msgs = mapBackendMessages(detail.messages);
        setMessages(activeSessionId, msgs);
        setIsLoadingMessages(false);
      })
      .catch((err) => {
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
    [
      setExtracting,
      setCandidates,
      setExtractError,
      setActiveTab,
      setRightPanelPreset,
    ],
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

  const markToolCallInterrupted = useCallback((sid: string, data: HitlData) => {
    const updateLast = useChatStore.getState().updateLastAssistantMessage;
    updateLast(sid, (msg) => ({
      ...msg,
      toolCalls: msg.toolCalls?.map((tc) =>
        tc.state === 'running'
          ? {
              ...tc,
              state: 'completed' as const,
              result: formatToolInterrupt(tc.name, data),
              durationMs:
                tc.durationMs ??
                (tc.startedAt !== undefined
                  ? Math.max(0, Date.now() - tc.startedAt)
                  : undefined),
            }
          : tc,
      ),
      hitlData: data,
    }));
  }, []);

  // Records 갱신 트리거
  const bumpRefresh = useArtifactRecordStore((s) => s.bumpRefresh);

  // Tool call 실행 디스패처
  const executeToolCall = useCallback(
    (sid: string, name: string) => {
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
    [
      currentProject,
      markToolCallError,
      triggerExtractRecords,
      triggerGenerateSrs,
    ],
  );

  // 백엔드 도구 실행 결과 처리
  const handleToolResult = useCallback(
    (
      sid: string,
      name: string,
      result: Record<string, unknown>,
      status?: 'success' | 'error',
      durationMs?: number,
    ) => {
      const updateLast = useChatStore.getState().updateLastAssistantMessage;

      if (
        [
          'create_record',
          'update_record',
          'delete_record',
          'update_record_status',
        ].includes(name)
      ) {
        bumpRefresh();
        useArtifactRefreshStore.getState().bump('record');
      }
      if (
        name === 'requirement' &&
        typeof result.records_approved_count === 'number' &&
        result.records_approved_count > 0
      ) {
        setActiveTab('records');
        bumpRefresh();
      }

      const agentToKind: Record<string, ArtifactKind> = {
        requirement: 'record',
        record_manager: 'record',
        srs_generator: 'srs',
        design_generator: 'design',
        testcase_generator: 'testcase',
      };
      const kind = agentToKind[name];
      if (kind) {
        useArtifactActionStore.getState().setGenerating(kind, false);
        if (status !== 'error') {
          useArtifactRefreshStore.getState().bump(kind);
        }
      }

      if (name === 'record_manager' && status !== 'error') {
        bumpRefresh();
      }

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
                error: isError
                  ? (result.error as string | undefined)
                  : undefined,
                durationMs: durationMs ?? tc.durationMs,
              }
            : tc,
        ),
      }));
    },
    [bumpRefresh, setActiveTab],
  );

  // sendMessage / resumeFromInterrupt 가 공유하는 SSE 콜백 빌더
  const buildStreamCallbacks = useCallback(
    (sid: string): StreamCallbacks => {
      const updateLastAssistant =
        useChatStore.getState().updateLastAssistantMessage;
      return {
        onToken: (token) => enqueueToken(sid, token),
        onToolCall: (toolCall) => {
          const tc: ToolCallData = {
            name: toolCall.name,
            arguments: toolCall.arguments,
            state: 'running',
            startedAt: Date.now(),
          };
          updateLastAssistant(sid, (msg) => ({
            ...msg,
            toolCalls: [...(msg.toolCalls ?? []), tc],
          }));

          const genKind: Record<string, ArtifactKind> = {
            srs_generator: 'srs',
            design_generator: 'design',
            system_model_generator: 'system_model',
            data_model_generator: 'data_model',
            testcase_generator: 'testcase',
          };
          const kind = genKind[toolCall.name];
          if (kind) {
            useArtifactActionStore.getState().setGenerating(kind, true);
            const tabMap: Record<string, string> = {
              record: 'records',
              system_model: 'design',
              data_model: 'design',
            };
            useArtifactStore
              .getState()
              .setActiveTab((tabMap[kind] ?? kind) as ArtifactType);
          }

          executeToolCall(sid, toolCall.name);
        },
        onToolResult: (toolResult) => {
          handleToolResult(
            sid,
            toolResult.name,
            toolResult.result,
            toolResult.status,
            toolResult.durationMs,
          );
        },
        onSources: (sources) => {
          updateLastAssistant(sid, (msg) => ({
            ...msg,
            sources,
          }));
        },
        onPlanUpdate: ({ plan, current_step }) => {
          updateLastAssistant(sid, (msg) => ({
            ...msg,
            plan,
            currentPlanStep: current_step,
          }));
        },
        onInterrupt: (data) => {
          markToolCallInterrupted(sid, data);
          upsertHitl({
            threadId: data.interrupt_id,
            sessionId: sid,
            data,
            createdAt: new Date().toISOString(),
          });
        },
        onDone: () => {
          requestFinishAfterDrain(sid, 'done');
          streamAbortControllers.delete(sid);
        },
        onError: (error) => {
          enqueueToken(sid, `\n\n${error}`);
          requestFinishAfterDrain(sid, 'error');
          streamAbortControllers.delete(sid);
        },
      };
    },
    [
      enqueueToken,
      executeToolCall,
      handleToolResult,
      markToolCallInterrupted,
      requestFinishAfterDrain,
      upsertHitl,
    ],
  );

  const resumeFromInterrupt = useCallback(
    (
      response: Record<string, unknown>,
      hitlThreadId?: string,
      hitlSessionId?: string,
    ) => {
      const threadId = hitlThreadId ?? pendingHitl?.threadId;
      const sid = hitlSessionId ?? pendingHitl?.sessionId;
      if (!threadId || !sid) return;

      removeHitl(threadId);

      const isApproved = response.action === 'approve';
      const updateByInterruptId =
        useChatStore.getState().updateMessageByInterruptId;
      let hitlKind: ArtifactKind | null = null;
      updateByInterruptId(sid, threadId, (msg) => {
        const ctx = (msg.hitlData as Record<string, unknown> | null)
          ?.context as Record<string, unknown> | undefined;
        const agentName = (ctx?.artifact_kind as string) ?? '';
        const kindMap: Record<string, ArtifactKind> = {
          srs_generator: 'srs',
          design_generator: 'design',
          testcase_generator: 'testcase',
          requirement: 'record',
        };
        hitlKind = kindMap[agentName] ?? null;
        return {
          ...msg,
          hitlResponded: true,
          hitlApproved: isApproved,
        };
      });

      if (isApproved && hitlKind) {
        useArtifactActionStore.getState().setGenerating(hitlKind, true);
        useArtifactStore
          .getState()
          .setActiveTab(hitlKind === 'record' ? 'records' : hitlKind);
      }

      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        content: '',
        status: 'streaming',
        createdAt: new Date().toISOString(),
      };
      addMessage(sid, assistantMsg);
      setSessionStreaming(sid, true);
      clearBufferedTokens(sid);

      const abort = streamAgentResume(
        { thread_id: threadId, response },
        buildStreamCallbacks(sid),
      );
      streamAbortControllers.set(sid, abort);
    },
    [
      pendingHitl,
      removeHitl,
      addMessage,
      setSessionStreaming,
      clearBufferedTokens,
      buildStreamCallbacks,
    ],
  );

  const sendMessage = useCallback(
    async (input: SendMessageInput) => {
      const { text, files } = normalizeSendInput(input);
      const trimmed = text.trim();
      if ((!trimmed && files.length === 0) || !currentProject || isStreaming) return;

      let targetSessionId = activeSessionId;

      if (!targetSessionId) {
        setIsCreatingSession(true);
        try {
          const newSession = await sessionService.create(
            currentProject.project_id,
            trimmed.slice(0, 40) || files[0]?.filename?.slice(0, 40),
          );
          targetSessionId = newSession.id;
          setIsCreatingSession(false);
        } catch {
          setIsCreatingSession(false);
          return;
        }
      }

      const uploadFiles = (
        await Promise.all(files.map((file) => filePartToFile(file)))
      ).filter((file): file is File => file !== null);
      const attachments = await uploadAgentAttachments(
        targetSessionId,
        uploadFiles,
      );

      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: trimmed,
        attachments: toChatAttachments(attachments),
        createdAt: new Date().toISOString(),
      };
      addMessage(targetSessionId, userMsg);
      setInputValue('');

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

      // 스토어에 메시지가 들어간 후 pendingSessionId 설정 + 네비게이션.
      // 순서 중요: addMessage → setPendingSessionId 해야
      // activeSessionId 변경 시 스토어에 이미 메시지가 있어 깜빡임 방지.
      if (!activeSessionId) {
        setPendingSessionId(targetSessionId);
        useChatStore.getState().bumpSessionListNonce();
        router.replace(`/agent/${targetSessionId}`);
      }

      const abort = streamAgentChat(
        {
          session_id: targetSessionId,
          message: trimmed,
          attachments,
        },
        buildStreamCallbacks(targetSessionId),
      );

      streamAbortControllers.set(targetSessionId, abort);
    },
    [
      currentProject,
      activeSessionId,
      isStreaming,
      addMessage,
      setInputValue,
      setSessionStreaming,
      clearBufferedTokens,
      buildStreamCallbacks,
      router,
    ],
  );

  // 스트리밍 중지
  const stopStreaming = useCallback(() => {
    if (!activeSessionId) return;
    flushBufferedTokens(activeSessionId);
    streamAbortControllers.get(activeSessionId)?.();
    streamAbortControllers.delete(activeSessionId);
    finishStreaming(activeSessionId);
  }, [activeSessionId, finishStreaming, flushBufferedTokens]);

  // Keep the SSE connection alive across route changes, but render any buffered
  // text before this view disappears so returning to the session feels current.
  useEffect(() => {
    return () => {
      if (sessionId) {
        flushBufferedTokens(sessionId);
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
    resumeFromInterrupt,
  };
}
