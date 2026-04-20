import { create } from 'zustand';

export interface ToolCallData {
  name: string;
  arguments: Record<string, unknown>;
  state: 'running' | 'completed' | 'error';
  result?: string;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  /** 메시지 상태 — undefined는 'done'과 동일 (서버 로드 메시지 호환) */
  status?: 'streaming' | 'done' | 'error';
  /** 구조화된 데이터 (clarify, requirements, generate_srs) */
  toolData?: {
    type: 'clarify' | 'requirements' | 'generate_srs';
    data: unknown;
  } | null;
  /** Function Calling 도구 호출 */
  toolCalls?: ToolCallData[];
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

  // 메시지 관리
  setMessages: (sessionId: string, messages: ChatMessage[]) => void;
  addMessage: (sessionId: string, message: ChatMessage) => void;
  appendToLastAssistant: (sessionId: string, token: string) => void;
  updateLastAssistantMessage: (sessionId: string, updater: (msg: ChatMessage) => ChatMessage) => void;
  clearSession: (sessionId: string) => void;
  getMessages: (sessionId: string) => ChatMessage[];

  // 스트리밍 상태
  isSessionStreaming: (sessionId: string) => boolean;
  setSessionStreaming: (sessionId: string, streaming: boolean) => void;
  /** message.status + streamingSessionIds를 원자적으로 업데이트 (재렌더 1회) */
  finishStreaming: (sessionId: string, status?: 'done' | 'error') => void;

  // 입력값
  setInputValue: (val: string) => void;

  // 세션 목록 갱신
  bumpSessionListNonce: () => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  sessionMessages: {},
  streamingSessionIds: new Set(),
  inputValue: '',
  sessionListNonce: 0,

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
      if (!last || last.role !== 'assistant') return s;

      const nextMessages = [...current];
      nextMessages[nextMessages.length - 1] = {
        ...last,
        content: last.content + token,
        status: 'streaming',
      };
      return { sessionMessages: { ...s.sessionMessages, [sessionId]: nextMessages } };
    }),

  updateLastAssistantMessage: (sessionId, updater) =>
    set((s) => {
      const msgs = [...(s.sessionMessages[sessionId] ?? [])];
      const last = msgs[msgs.length - 1];
      if (last?.role === 'assistant') {
        msgs[msgs.length - 1] = updater(last);
      }
      return { sessionMessages: { ...s.sessionMessages, [sessionId]: msgs } };
    }),

  clearSession: (sessionId) =>
    set((s) => {
      const { [sessionId]: _, ...rest } = s.sessionMessages;
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

  finishStreaming: (sessionId, status = 'done') =>
    set((s) => {
      const current = s.sessionMessages[sessionId] ?? [];
      const last = current[current.length - 1];
      let nextMessages = current;
      if (last?.role === 'assistant' && last.status === 'streaming') {
        nextMessages = [...current];
        nextMessages[nextMessages.length - 1] = { ...last, status };
      }
      const next = new Set(s.streamingSessionIds);
      next.delete(sessionId);
      return {
        sessionMessages: { ...s.sessionMessages, [sessionId]: nextMessages },
        streamingSessionIds: next,
      };
    }),

  setInputValue: (val) => set({ inputValue: val }),

  bumpSessionListNonce: () => set((s) => ({ sessionListNonce: s.sessionListNonce + 1 })),
}));
