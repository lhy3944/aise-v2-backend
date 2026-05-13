import { useChatStore } from '@/stores/chat-store';
import { useCallback, useEffect, useRef } from 'react';

interface UseTokenDrainOptions {
  isMobile: boolean;
}

/**
 * SSE 토큰 버퍼링 — 모바일/데스크탑별 청크 크기와 드레인 주기를 조절해
 * 잦은 setState 호출을 줄이고 자연스러운 타이핑 효과를 제공한다.
 */
export function useTokenDrain({ isMobile }: UseTokenDrainOptions) {
  const appendToLastAssistant = useChatStore((s) => s.appendToLastAssistant);
  const finishStreaming = useChatStore((s) => s.finishStreaming);

  const tokenBufferRef = useRef<Map<string, string>>(new Map());
  const tokenDrainTimerRef = useRef<Map<string, number>>(new Map());
  const pendingFinishStatusRef = useRef<Map<string, 'done' | 'error'>>(
    new Map(),
  );
  const scheduleTokenDrainRef = useRef<
    (sid: string, immediate?: boolean) => void
  >(() => {});

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
          scheduleTokenDrainRef.current(sid);
        }
      }, delay);

      tokenDrainTimerRef.current.set(sid, timerId);
    },
    [appendToLastAssistant, finishStreaming, isMobile],
  );

  useEffect(() => {
    scheduleTokenDrainRef.current = scheduleTokenDrain;
  }, [scheduleTokenDrain]);

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

  return {
    clearBufferedTokens,
    flushBufferedTokens,
    enqueueToken,
    requestFinishAfterDrain,
  };
}
