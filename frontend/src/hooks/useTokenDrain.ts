import { useChatStore } from '@/stores/chat-store';
import { useCallback, useEffect, useRef } from 'react';

interface UseTokenDrainOptions {
  isMobile: boolean;
}

const tokenBuffer = new Map<string, string>();
const tokenDrainTimers = new Map<string, number>();
const pendingFinishStatus = new Map<string, 'done' | 'error'>();

/**
 * Buffers SSE tokens per session. The backing maps live at module scope so a
 * stream can continue draining even when the chat page unmounts during route
 * changes.
 */
export function useTokenDrain({ isMobile }: UseTokenDrainOptions) {
  const appendToLastAssistant = useChatStore((s) => s.appendToLastAssistant);
  const finishStreaming = useChatStore((s) => s.finishStreaming);
  const scheduleTokenDrainRef = useRef<
    (sid: string, immediate?: boolean) => void
  >(() => {});

  const clearBufferedTokens = useCallback((sid: string) => {
    tokenBuffer.delete(sid);
    pendingFinishStatus.delete(sid);
    const timerId = tokenDrainTimers.get(sid);
    if (timerId !== undefined) {
      clearTimeout(timerId);
      tokenDrainTimers.delete(sid);
    }
  }, []);

  const scheduleTokenDrain = useCallback(
    (sid: string, immediate = false) => {
      if (tokenDrainTimers.has(sid)) return;

      const delay = immediate ? 0 : isMobile ? 18 : 10;
      const timerId = window.setTimeout(() => {
        tokenDrainTimers.delete(sid);

        const buffered = tokenBuffer.get(sid) ?? '';
        if (!buffered) {
          const pendingStatus = pendingFinishStatus.get(sid);
          if (pendingStatus) {
            pendingFinishStatus.delete(sid);
            finishStreaming(sid, pendingStatus);
          }
          return;
        }

        const chunkSize = isMobile ? 28 : 120;
        const nextChunk = buffered.slice(0, chunkSize);
        const rest = buffered.slice(chunkSize);

        appendToLastAssistant(sid, nextChunk);

        if (rest) tokenBuffer.set(sid, rest);
        else tokenBuffer.delete(sid);

        if (tokenBuffer.has(sid) || pendingFinishStatus.has(sid)) {
          scheduleTokenDrainRef.current(sid);
        }
      }, delay);

      tokenDrainTimers.set(sid, timerId);
    },
    [appendToLastAssistant, finishStreaming, isMobile],
  );

  useEffect(() => {
    scheduleTokenDrainRef.current = scheduleTokenDrain;
  }, [scheduleTokenDrain]);

  const flushBufferedTokens = useCallback(
    (sid: string) => {
      const timerId = tokenDrainTimers.get(sid);
      if (timerId !== undefined) {
        clearTimeout(timerId);
        tokenDrainTimers.delete(sid);
      }

      const buffered = tokenBuffer.get(sid);
      if (buffered) {
        appendToLastAssistant(sid, buffered);
      }
      tokenBuffer.delete(sid);

      const pendingStatus = pendingFinishStatus.get(sid);
      if (pendingStatus) {
        pendingFinishStatus.delete(sid);
        finishStreaming(sid, pendingStatus);
      }
    },
    [appendToLastAssistant, finishStreaming],
  );

  const enqueueToken = useCallback(
    (sid: string, token: string) => {
      const prev = tokenBuffer.get(sid) ?? '';
      tokenBuffer.set(sid, prev + token);
      scheduleTokenDrain(sid, true);
    },
    [scheduleTokenDrain],
  );

  const requestFinishAfterDrain = useCallback(
    (sid: string, status: 'done' | 'error') => {
      pendingFinishStatus.set(sid, status);
      scheduleTokenDrain(sid);
    },
    [scheduleTokenDrain],
  );

  return {
    clearBufferedTokens,
    flushBufferedTokens,
    enqueueToken,
    requestFinishAfterDrain,
  };
}
