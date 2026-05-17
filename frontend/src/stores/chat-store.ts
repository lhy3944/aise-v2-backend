import { create } from "zustand";

import type { HitlData, PlanStep, SourceRef } from "@/types/agent-events";

export interface ToolCallData {
  name: string;
  arguments: Record<string, unknown>;
  state: "running" | "completed" | "error";
  result?: string;
  error?: string;
  /** Unix ms — when the tool_call SSE arrived (for live elapsed timer) */
  startedAt?: number;
  /** Backend-measured duration from tool_result SSE (preferred over
   *  client-side elapsed once tool_result arrives) */
  durationMs?: number;
}

export interface ChatAttachment {
  id: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  storageKey?: string;
  textPreview?: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  /** 메시지 상태 — undefined는 'done'과 동일 (서버 로드 메시지 호환) */
  status?: "streaming" | "done" | "error";
  /** 구조화된 데이터 (clarify, requirements, generate_srs) */
  toolData?: {
    type: "clarify" | "requirements" | "generate_srs";
    data: unknown;
  } | null;
  /** Function Calling 도구 호출 */
  toolCalls?: ToolCallData[];
  /** User-uploaded files attached to this turn. Originals are stored in MinIO. */
  attachments?: ChatAttachment[];
  /** RAG 출처 — SSE `sources` 이벤트 수신 시 세팅. 본문 `[N]` 인용 앵커와 매칭. */
  sources?: SourceRef[];
  /** Supervisor 가 plan 실행을 결정한 경우 step 진행 상태. plan_update SSE 누적. */
  plan?: PlanStep[];
  /** plan 내 현재 실행 중 step 인덱스 (0-based). */
  currentPlanStep?: number;
  /** HITL interrupt 데이터 — 인라인 카드로 렌더링. */
  hitlData?: HitlData | null;
  /** HITL 카드 응답 완료 여부 */
  hitlResponded?: boolean;
  /** HITL 카드 승인 여부 (true=승인, false=거부) */
  hitlApproved?: boolean | null;
  /** HITL 승인 후 산출물 생성 완료 여부 — 스트리밍 종료 시 true */
  hitlArtifactDone?: boolean;
  createdAt: string;
}

interface ChatState {
  /** 세션별 메시지 캐시 (서버에서 로드 + 실시간 스트리밍) */
  sessionMessages: Record<string, ChatMessage[]>;
  /** 스트리밍 중인 세션 ID 집합 */
  streamingSessionIds: Set<string>;

  inputValue: string;

  /** 세션 목록 갱신 트리거 (새 세션 생성 시 bump) */
  sessionListNonce: number;
  sessionFavorites: Record<string, boolean>;

  // 메시지 관리
  setMessages: (sessionId: string, messages: ChatMessage[]) => void;
  addMessage: (sessionId: string, message: ChatMessage) => void;
  appendToLastAssistant: (sessionId: string, token: string) => void;
  updateLastAssistantMessage: (
    sessionId: string,
    updater: (msg: ChatMessage) => ChatMessage,
  ) => void;
  updateMessageByInterruptId: (
    sessionId: string,
    interruptId: string,
    updater: (msg: ChatMessage) => ChatMessage,
  ) => void;
  clearSession: (sessionId: string) => void;
  getMessages: (sessionId: string) => ChatMessage[];

  // 스트리밍 상태
  isSessionStreaming: (sessionId: string) => boolean;
  setSessionStreaming: (sessionId: string, streaming: boolean) => void;
  /** message.status + streamingSessionIds를 원자적으로 업데이트 (재렌더 1회) */
  finishStreaming: (sessionId: string, status?: "done" | "error") => void;

  // 입력값
  setInputValue: (val: string) => void;

  // 세션 목록 갱신
  bumpSessionListNonce: () => void;
  setSessionFavorite: (sessionId: string, isFavorite: boolean) => void;
  setSessionFavorites: (favorites: Record<string, boolean>) => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  sessionMessages: {},
  streamingSessionIds: new Set(),
  inputValue: "",
  sessionListNonce: 0,
  sessionFavorites: {},

  setMessages: (sessionId, messages) =>
    set((s) => ({
      sessionMessages: { ...s.sessionMessages, [sessionId]: messages },
    })),

  addMessage: (sessionId, message) =>
    set((s) => ({
      sessionMessages: {
        ...s.sessionMessages,
        [sessionId]: [...(s.sessionMessages[sessionId] ?? []), message],
      },
    })),

  appendToLastAssistant: (sessionId, token) =>
    set((s) => {
      const current = s.sessionMessages[sessionId] ?? [];
      const last = current[current.length - 1];
      if (!last || last.role !== "assistant") return s;

      const nextMessages = [...current];
      nextMessages[nextMessages.length - 1] = {
        ...last,
        content: last.content + token,
        status: "streaming",
      };
      return {
        sessionMessages: { ...s.sessionMessages, [sessionId]: nextMessages },
      };
    }),

  updateLastAssistantMessage: (sessionId, updater) =>
    set((s) => {
      const msgs = [...(s.sessionMessages[sessionId] ?? [])];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = updater(last);
      }
      return { sessionMessages: { ...s.sessionMessages, [sessionId]: msgs } };
    }),

  updateMessageByInterruptId: (sessionId, interruptId, updater) =>
    set((s) => {
      const msgs = [...(s.sessionMessages[sessionId] ?? [])];
      const idx = msgs.findIndex(
        (m) => m.hitlData?.interrupt_id === interruptId,
      );
      if (idx !== -1) {
        msgs[idx] = updater(msgs[idx]);
        return { sessionMessages: { ...s.sessionMessages, [sessionId]: msgs } };
      }
      return s;
    }),

  clearSession: (sessionId) =>
    set((s) => {
      const rest = { ...s.sessionMessages };
      delete rest[sessionId];
      return { sessionMessages: rest };
    }),

  getMessages: (sessionId) => get().sessionMessages[sessionId] ?? [],

  isSessionStreaming: (sessionId) => get().streamingSessionIds.has(sessionId),

  setSessionStreaming: (sessionId, streaming) =>
    set((s) => {
      const next = new Set(s.streamingSessionIds);
      if (streaming) next.add(sessionId);
      else next.delete(sessionId);
      return { streamingSessionIds: next };
    }),

  finishStreaming: (sessionId, status = "done") =>
    set((s) => {
      const current = s.sessionMessages[sessionId] ?? [];
      const last = current[current.length - 1];
      let nextMessages = current;
      if (last?.role === "assistant" && last.status === "streaming") {
        nextMessages = [...current];
        nextMessages[nextMessages.length - 1] = { ...last, status };
      }
      // HITL 승인 후 스트리밍 완료 → 해당 카드에 artifactDone 표시
      // 이후 동일 세션에서 새 스트리밍이 시작되어도 이전 카드 스피너가 재활성화되지 않음
      const hasPendingHITL = nextMessages.some(
        (m) => m.hitlResponded && m.hitlApproved && !m.hitlArtifactDone,
      );
      if (hasPendingHITL) {
        nextMessages = nextMessages.map((m) =>
          m.hitlResponded && m.hitlApproved && !m.hitlArtifactDone
            ? { ...m, hitlArtifactDone: true }
            : m,
        );
      }
      const next = new Set(s.streamingSessionIds);
      next.delete(sessionId);
      return {
        sessionMessages: { ...s.sessionMessages, [sessionId]: nextMessages },
        streamingSessionIds: next,
      };
    }),

  setInputValue: (val) => set({ inputValue: val }),

  bumpSessionListNonce: () =>
    set((s) => ({ sessionListNonce: s.sessionListNonce + 1 })),

  setSessionFavorite: (sessionId, isFavorite) =>
    set((s) => ({
      sessionFavorites: { ...s.sessionFavorites, [sessionId]: isFavorite },
    })),

  setSessionFavorites: (favorites) =>
    set((s) => ({
      sessionFavorites: { ...s.sessionFavorites, ...favorites },
    })),
}));
