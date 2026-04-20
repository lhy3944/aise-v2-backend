/**
 * Agent Chat SSE 스트리밍 서비스
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export interface AgentChatRequest {
  session_id: string;
  message: string;
}

export interface ToolCallEvent {
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultEvent {
  name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface SSEEvent {
  type: 'token' | 'tool_call' | 'tool_result' | 'done' | 'error';
  content?: string;
  name?: string;
  arguments?: Record<string, unknown>;
  result?: Record<string, unknown>;
}

/**
 * Agent Chat SSE 스트리밍 호출
 * @returns abort 함수
 */
export function streamAgentChat(
  request: AgentChatRequest,
  callbacks: {
    onToken: (token: string) => void;
    onToolCall: (toolCall: ToolCallEvent) => void;
    onToolResult?: (toolResult: ToolResultEvent) => void;
    onDone: () => void;
    onError: (error: string) => void;
  },
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        callbacks.onError(`서버 오류: ${response.status} ${errorText}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError('스트리밍을 시작할 수 없습니다.');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event: SSEEvent = JSON.parse(jsonStr);
            switch (event.type) {
              case 'token':
                if (event.content) callbacks.onToken(event.content);
                break;
              case 'tool_call':
                if (event.name) {
                  callbacks.onToolCall({
                    name: event.name,
                    arguments: event.arguments ?? {},
                  });
                }
                break;
              case 'tool_result':
                if (event.name && callbacks.onToolResult) {
                  callbacks.onToolResult({
                    name: event.name,
                    arguments: event.arguments ?? {},
                    result: event.result ?? {},
                  });
                }
                break;
              case 'done':
                callbacks.onDone();
                return;
              case 'error':
                callbacks.onError(event.content ?? '알 수 없는 오류');
                return;
            }
          } catch {
            // JSON 파싱 실패 — 무시
          }
        }
      }

      callbacks.onDone();
    } catch (err) {
      if (controller.signal.aborted) return;
      callbacks.onError(err instanceof Error ? err.message : '네트워크 오류');
    }
  })();

  return () => controller.abort();
}
