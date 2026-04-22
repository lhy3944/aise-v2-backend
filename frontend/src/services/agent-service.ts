/**
 * Agent Chat SSE streaming service.
 *
 * Transport: @microsoft/fetch-event-source (POST + custom headers + better
 * error/reconnect handling than the raw fetch+ReadableStream loop).
 *
 * Envelope: AgentStreamEvent per docs/events.md — `{"type": "...", "data": {...}}`.
 *
 * Token buffering and mobile chunking stay in useChatStream.ts — this module
 * only parses the wire format and invokes callbacks.
 */

import {
  fetchEventSource,
  type EventSourceMessage,
} from '@microsoft/fetch-event-source';

import type {
  AgentStreamEvent,
  ArtifactCreatedEvent,
  HitlData,
  InterruptEvent,
  PlanStep,
  PlanUpdateEvent,
  SourceRef,
} from '@/types/agent-events';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export interface AgentChatRequest {
  session_id: string;
  message: string;
}

export interface ToolCallEvent {
  name: string;
  arguments: Record<string, unknown>;
  tool_call_id?: string;
  agent?: string;
}

export interface ToolResultEvent {
  name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
  tool_call_id?: string;
  status?: 'success' | 'error';
  duration_ms?: number;
}

interface WireEvent {
  type: string;
  data?: Record<string, unknown>;
}

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onToolCall: (toolCall: ToolCallEvent) => void;
  onToolResult?: (toolResult: ToolResultEvent) => void;
  onDone: () => void;
  onError: (error: string) => void;

  onPlanUpdate?: (update: { plan: PlanStep[]; current_step?: number }) => void;
  onInterrupt?: (hitl: HitlData) => void;
  onArtifactCreated?: (artifact: ArtifactCreatedEvent['data']) => void;
  onSources?: (sources: SourceRef[], agent?: string) => void;
}

function dispatch(event: WireEvent, cb: StreamCallbacks): 'continue' | 'stop' {
  const d = (event.data ?? {}) as Record<string, unknown>;
  switch (event.type as AgentStreamEvent['type']) {
    case 'token': {
      const text = d.text;
      if (typeof text === 'string' && text.length > 0) cb.onToken(text);
      return 'continue';
    }
    case 'tool_call': {
      const name = typeof d.name === 'string' ? d.name : '';
      if (!name) return 'continue';
      cb.onToolCall({
        name,
        arguments: (d.arguments as Record<string, unknown>) ?? {},
        tool_call_id: typeof d.tool_call_id === 'string' ? d.tool_call_id : undefined,
        agent: typeof d.agent === 'string' ? d.agent : undefined,
      });
      return 'continue';
    }
    case 'tool_result': {
      const name = typeof d.name === 'string' ? d.name : '';
      if (!name || !cb.onToolResult) return 'continue';
      cb.onToolResult({
        name,
        arguments: {},
        result: (d.result as Record<string, unknown>) ?? {},
        tool_call_id: typeof d.tool_call_id === 'string' ? d.tool_call_id : undefined,
        status: d.status === 'error' ? 'error' : 'success',
        duration_ms: typeof d.duration_ms === 'number' ? d.duration_ms : undefined,
      });
      return 'continue';
    }
    case 'plan_update':
      cb.onPlanUpdate?.((event as unknown as PlanUpdateEvent).data);
      return 'continue';
    case 'interrupt':
      cb.onInterrupt?.((event as unknown as InterruptEvent).data);
      return 'continue';
    case 'artifact_created':
      cb.onArtifactCreated?.((event as unknown as ArtifactCreatedEvent).data);
      return 'continue';
    case 'sources': {
      const sources = d.sources;
      if (Array.isArray(sources)) {
        cb.onSources?.(
          sources as SourceRef[],
          typeof d.agent === 'string' ? d.agent : undefined,
        );
      }
      return 'continue';
    }
    case 'done':
      cb.onDone();
      return 'stop';
    case 'error': {
      const message = typeof d.message === 'string' ? d.message : '알 수 없는 오류';
      cb.onError(message);
      return 'stop';
    }
    default:
      return 'continue';
  }
}

class FatalStreamError extends Error {}

/**
 * Start an Agent Chat SSE stream.
 *
 * @returns abort() — idempotent; safe to call after completion.
 */
export function streamAgentChat(
  request: AgentChatRequest,
  callbacks: StreamCallbacks,
): () => void {
  const controller = new AbortController();
  let closed = false;

  const close = () => {
    if (!closed) {
      closed = true;
      controller.abort();
    }
  };

  (async () => {
    try {
      await fetchEventSource(`${API_BASE}/api/v1/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(request),
        signal: controller.signal,
        // Prevent the library from reconnecting when the tab is backgrounded —
        // we treat the stream as a one-shot request.
        openWhenHidden: true,

        async onopen(response) {
          if (!response.ok) {
            const text = await response.text().catch(() => '');
            throw new FatalStreamError(`서버 오류: ${response.status} ${text}`);
          }
          const ct = response.headers.get('content-type') ?? '';
          if (!ct.includes('text/event-stream')) {
            throw new FatalStreamError(`잘못된 응답 타입: ${ct || 'unknown'}`);
          }
        },

        onmessage(msg: EventSourceMessage) {
          if (!msg.data) return;
          let parsed: WireEvent;
          try {
            parsed = JSON.parse(msg.data);
          } catch {
            return; // malformed line — drop silently (contract invariant)
          }
          const outcome = dispatch(parsed, callbacks);
          if (outcome === 'stop') close();
        },

        onclose() {
          // Peer closed. If we never saw a terminal event, emit onDone so the
          // UI exits the streaming state cleanly.
          if (!closed) {
            close();
            callbacks.onDone();
          }
        },

        onerror(err) {
          // Throwing aborts the retry loop; returning undefined would retry.
          throw err instanceof Error ? err : new FatalStreamError(String(err));
        },
      });
    } catch (err) {
      if (controller.signal.aborted) return;
      const message =
        err instanceof FatalStreamError
          ? err.message
          : err instanceof Error
            ? err.message
            : '네트워크 오류';
      callbacks.onError(message);
    }
  })();

  return close;
}
