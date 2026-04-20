'use client';

import type { ChatMessage } from '@/stores/chat-store';
import { usePanelStore } from '@/stores/panel-store';
import { useCallback, useEffect, useRef, useState } from 'react';

const BOTTOM_THRESHOLD = 80;

export function useChatScroll(messages: ChatMessage[]) {
  const isMobile = usePanelStore((s) => s.isMobile);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [mountVersion, setMountVersion] = useState(0);
  const [isAtBottom, setIsAtBottom] = useState(true);
  // 자동 스크롤 판단용 — state가 effect dep에 들어가면 사용자가 threshold 안쪽으로
  // 스크롤하는 순간 effect가 재실행돼 "자석처럼 붙는" 점프가 발생한다.
  // ref로 분리해서 dep에서 제외하고, messages 변화 시에만 최신 값을 읽어 판단한다.
  const isAtBottomRef = useRef(true);

  // callback ref — AnimatePresence 등으로 ScrollArea 마운트가 지연되어도
  // viewport가 attach되는 시점에 리렌더를 유발해서 scroll listener 등록을 보장.
  const setScrollEl = useCallback((el: HTMLDivElement | null) => {
    scrollRef.current = el;
    setMountVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handleScroll = () => {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      const atBottom = distanceFromBottom <= BOTTOM_THRESHOLD;
      isAtBottomRef.current = atBottom;
      setIsAtBottom(atBottom);
    };
    // 초기 상태 반영을 rAF로 지연 — useEffect 본문 동기 setState 회피
    const raf = requestAnimationFrame(handleScroll);
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      el.removeEventListener('scroll', handleScroll);
    };
  }, [mountVersion]);

  const hasCurrentTurn =
    messages.length >= 2 &&
    messages[messages.length - 2]?.role === 'user' &&
    messages[messages.length - 1]?.role === 'assistant';
  // 모바일은 현재 턴을 상단 고정하되, 사용자가 하단 근처로 내려오면 자동 follow를 허용한다.
  const shouldPinCurrentTurn = isMobile && hasCurrentTurn && !isAtBottom;

  useEffect(() => {
    if (shouldPinCurrentTurn) return;
    if (isAtBottomRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, shouldPinCurrentTurn, mountVersion]);

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, []);

  return { scrollRef, setScrollEl, isAtBottom, scrollToBottom };
}
