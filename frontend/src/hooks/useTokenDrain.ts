import { useChatStore } from '@/stores/chat-store';
import { useCallback, useRef } from 'react';

interface UseTokenDrainOptions {
  isMobile: boolean;
}

/**
 * Throttle 기반 토큰 드레인 (AI SDK Elements 방식).
 *
 * LLM 토큰을 mutable 버퍼에 즉시 누적하고,
 * 50ms(throttle) 간격으로 React state에 flush 한다.
 *
 * rAF와 달리 일정 간격으로 작은 청크를 Streamdown에 전달하므로
 * CSS staggered animation의 delay가 순서대로 적용되어
 * 시각적으로 순차적인 타이핑 효과가 보장된다.
 *
 * 성능: 초당 최대 30회 리렌더 (33ms throttle)
 * 모바일: 초당 최대 15회 리렌더 (66ms throttle)
 */
export function useTokenDrain({ isMobile }: UseTokenDrainOptions) {
  const appendToLastAssistant = useChatStore((s) => s.appendToLastAssistant);
  const finishStreaming = useChatStore((s) => s.finishStreaming);

  // 모듈 스코프: 컴포넌트 리렌더와 무관하게 유지
  const storeRef = useRef({
    buffers: new Map<string, string>(),
    pendingFinish: new Map<string, 'done' | 'error'>(),
    timers: new Map<string, ReturnType<typeof setTimeout>>(),
  });

  const THROTTLE_MS = isMobile ? 66 : 33;

  const drain = useCallback(
    (sid: string) => {
      const { buffers, pendingFinish, timers } = storeRef.current;
      timers.delete(sid);

      const buffered = buffers.get(sid);
      if (buffered) {
        buffers.delete(sid);
        appendToLastAssistant(sid, buffered);
      }

      const pendingStatus = pendingFinish.get(sid);
      if (!buffers.has(sid) && pendingStatus) {
        pendingFinish.delete(sid);
        finishStreaming(sid, pendingStatus);
        return;
      }

      // 버퍼에 더 쌓인 토큰이 있으면 다음 throttle tick에서 계속
      if (buffers.has(sid)) {
        timers.set(sid, setTimeout(() => drain(sid), THROTTLE_MS));
      }
    },
    [appendToLastAssistant, finishStreaming, THROTTLE_MS],
  );

  const scheduleDrain = useCallback(
    (sid: string) => {
      const { timers } = storeRef.current;
      if (timers.has(sid)) return;
      timers.set(sid, setTimeout(() => drain(sid), THROTTLE_MS));
    },
    [drain],
  );

  const clearBufferedTokens = useCallback((sid: string) => {
    const { buffers, pendingFinish, timers } = storeRef.current;
    buffers.delete(sid);
    pendingFinish.delete(sid);
    const t = timers.get(sid);
    if (t !== undefined) {
      clearTimeout(t);
      timers.delete(sid);
    }
  }, []);

  const flushBufferedTokens = useCallback(
    (sid: string) => {
      const { buffers, pendingFinish, timers } = storeRef.current;
      const t = timers.get(sid);
      if (t !== undefined) {
        clearTimeout(t);
        timers.delete(sid);
      }

      const buffered = buffers.get(sid);
      if (buffered) {
        appendToLastAssistant(sid, buffered);
      }
      buffers.delete(sid);

      const pendingStatus = pendingFinish.get(sid);
      if (pendingStatus) {
        pendingFinish.delete(sid);
        finishStreaming(sid, pendingStatus);
      }
    },
    [appendToLastAssistant, finishStreaming],
  );

  const enqueueToken = useCallback(
    (sid: string, token: string) => {
      const { buffers } = storeRef.current;
      const prev = buffers.get(sid) ?? '';
      buffers.set(sid, prev + token);
      scheduleDrain(sid);
    },
    [scheduleDrain],
  );

  const requestFinishAfterDrain = useCallback(
    (sid: string, status: 'done' | 'error') => {
      const { pendingFinish } = storeRef.current;
      pendingFinish.set(sid, status);
      scheduleDrain(sid);
    },
    [scheduleDrain],
  );

  return {
    clearBufferedTokens,
    flushBufferedTokens,
    enqueueToken,
    requestFinishAfterDrain,
  };
}
