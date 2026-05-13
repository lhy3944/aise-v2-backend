'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ListFilterPlus } from 'lucide-react';
import { SessionItem } from '@/components/chat/SessionItem';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import { sessionService } from '@/services/session-service';
import type { SessionResponse } from '@/services/session-service';
import { useChatStore } from '@/stores/chat-store';
import { useHitlStore } from '@/stores/hitl-store';
import { useProjectStore } from '@/stores/project-store';

const SKELETON_WIDTHS = [72, 58, 85, 63, 91, 54, 78, 67];

function SessionListSkeleton() {
  return (
    <div className='flex flex-col gap-1.5 px-1'>
      {SKELETON_WIDTHS.map((width, i) => (
        <div key={i} className='flex items-center gap-2 px-2.5 py-2'>
          <Skeleton className='h-3.5 w-3.5 shrink-0 rounded' />
          <Skeleton className='h-3.5 rounded' style={{ width: `${width}%` }} />
        </div>
      ))}
    </div>
  );
}

interface SessionListProps {
  onSessionSelect?: () => void;
}

export function SessionList({ onSessionSelect }: SessionListProps) {
  const router = useRouter();
  const params = useParams();
  const rawSessionId = params?.sessionId;
  const activeSessionId = Array.isArray(rawSessionId)
    ? rawSessionId[0]
    : (rawSessionId as string | undefined);

  const currentProject = useProjectStore((s) => s.currentProject);
  const sessionListNonce = useChatStore((s) => s.sessionListNonce);
  const openHitlForSession = useHitlStore((s) => s.openForSession);
  const clearHitlSession = useHitlStore((s) => s.clearSession);

  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetchingMore, setIsFetchingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const projectIdRef = useRef(currentProject?.project_id);

  const viewportRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const fetchSessions = useCallback(async () => {
    if (!currentProject) {
      setSessions([]);
      setIsLoading(false);
      setNextCursor(null);
      return;
    }
    try {
      setIsLoading(true);
      const res = await sessionService.list(currentProject.project_id);
      setSessions(res.sessions);
      setNextCursor(res.next_cursor);
    } catch {
      setSessions([]);
      setNextCursor(null);
    } finally {
      setIsLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    const currentId = currentProject?.project_id;
    if (currentId !== projectIdRef.current) {
      projectIdRef.current = currentId;
      setSessions([]);
      setNextCursor(null);
    }
    void Promise.resolve().then(fetchSessions);
  }, [fetchSessions, sessionListNonce]);

  const fetchMore = useCallback(async () => {
    if (!currentProject || !nextCursor || isFetchingMore) return;
    try {
      setIsFetchingMore(true);
      const res = await sessionService.list(
        currentProject.project_id,
        nextCursor,
      );
      setSessions((prev) => [...prev, ...res.sessions]);
      setNextCursor(res.next_cursor);
    } catch {
      // 실패 시 재시도 가능하도록 cursor 유지
    } finally {
      setIsFetchingMore(false);
    }
  }, [currentProject, nextCursor, isFetchingMore]);

  // IntersectionObserver 기반 무한 스크롤
  useEffect(() => {
    const sentinel = sentinelRef.current;
    const viewport = viewportRef.current;
    if (!sentinel || !viewport || !nextCursor) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isFetchingMore) {
          void fetchMore();
        }
      },
      { root: viewport, rootMargin: '200px', threshold: 0 },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [nextCursor, isFetchingMore, fetchMore]);

  const handleDelete = useCallback(
    async (sessionId: string) => {
      try {
        await sessionService.delete(sessionId);
        clearHitlSession(sessionId);
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (activeSessionId === sessionId) {
          router.push('/agent');
        }
      } catch {
        // 에러 무시 (글로벌 핸들링)
      }
    },
    [activeSessionId, clearHitlSession, router],
  );

  const handleRename = useCallback(
    async (sessionId: string, newTitle: string) => {
      try {
        await sessionService.update(sessionId, newTitle);
        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s)),
        );
      } catch {
        // 에러 무시
      }
    },
    [],
  );

  return (
    <div className='flex min-h-0 flex-1 flex-col'>
      <div className='flex shrink-0 items-center justify-between px-2 pb-2'>
        <h3 className='text-fg-muted text-xs font-medium'>모든 작업</h3>
        <button
          type='button'
          aria-label='필터'
          className='text-icon-default hover:text-icon-active hover:bg-canvas-secondary cursor-pointer rounded-md p-1.5 transition-colors'
        >
          <ListFilterPlus className='size-4' />
        </button>
      </div>

      {isLoading ? (
        <SessionListSkeleton />
      ) : (
        <ScrollArea viewportRef={viewportRef} className='min-h-0 flex-1'>
          {sessions.map((session) => (
            <div key={session.id} className='mb-px'>
              <SessionItem
                session={session}
                isActive={session.id === activeSessionId}
                onClick={() => {
                  openHitlForSession(session.id);
                  router.push(`/agent/${session.id}`);
                  onSessionSelect?.();
                }}
                onDelete={() => handleDelete(session.id)}
                onRename={(title) => handleRename(session.id, title)}
              />
            </div>
          ))}

          {nextCursor && !isFetchingMore && (
            <div ref={sentinelRef} className='h-1' />
          )}

          {isFetchingMore && (
            <div className='flex items-center justify-center gap-2 py-3'>
              <Spinner size='size-3.5' className='text-fg-muted' />
            </div>
          )}
        </ScrollArea>
      )}
    </div>
  );
}
