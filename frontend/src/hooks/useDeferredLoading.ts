import { useCallback, useEffect, useRef, useSyncExternalStore } from 'react';

/**
 * 로딩 스켈레톤의 깜빡임을 방지
 * - loading이 true가 된 후 delay(기본 300ms) 이내에 false가 되면 스켈레톤 미표시
 * - delay를 넘기면 스켈레톤 표시, 한 번 표시되면 최소 minDuration(기본 400ms) 동안 유지
 */
export function useDeferredLoading(
  loading: boolean,
  delay = 300,
  minDuration = 400,
): boolean {
  const showRef = useRef(false);
  const shownAtRef = useRef<number | null>(null);
  const listenerRef = useRef<(() => void) | null>(null);

  const subscribe = useCallback((onStoreChange: () => void) => {
    listenerRef.current = onStoreChange;
    return () => {
      listenerRef.current = null;
    };
  }, []);

  const getSnapshot = useCallback(() => showRef.current, []);

  useEffect(() => {
    if (loading) {
      if (showRef.current) return;

      const timer = setTimeout(() => {
        showRef.current = true;
        shownAtRef.current = Date.now();
        listenerRef.current?.();
      }, delay);

      return () => clearTimeout(timer);
    }

    if (!showRef.current) return;

    const elapsed = Date.now() - (shownAtRef.current ?? 0);
    const remaining = Math.max(0, minDuration - elapsed);

    const timer = setTimeout(() => {
      showRef.current = false;
      shownAtRef.current = null;
      listenerRef.current?.();
    }, remaining);

    return () => clearTimeout(timer);
  }, [loading, delay, minDuration]);

  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
