'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ListFilterPlus } from 'lucide-react';
import { SessionItem } from '@/components/chat/SessionItem';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
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
  // `/agent/[[...sessionId]]`는 catch-all 라우트라 params.sessionId가 배열이다.
  // 그냥 `as string`으로 캐스트하면 `"id" === ["id"]` 비교가 false가 되어
  // active 하이라이트가 안 된다.
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

  const fetchSessions = useCallback(async () => {
    if (!currentProject) {
      setSessions([]);
      setIsLoading(false);
      return;
    }
    try {
      setIsLoading(true);
      const res = await sessionService.list(currentProject.project_id);
      setSessions(res.sessions);
    } catch {
      setSessions([]);
    } finally {
      setIsLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions, sessionListNonce]);

  // 세션 삭제 후 리패치 + 현재 세션이면 리다이렉트
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
      <div className='flex items-center justify-between px-2 pb-2'>
        <h3 className='text-fg-muted text-xs font-medium'>모든 작업</h3>
        <button
          type='button'
          aria-label='필터'
          className='text-icon-default hover:text-icon-active hover:bg-canvas-secondary cursor-pointer rounded-md p-1.5 transition-colors'
        >
          <ListFilterPlus className='size-4' />
        </button>
      </div>
      <ScrollArea type='always' className='flex-1 overflow-hidden'>
        {isLoading ? (
          <SessionListSkeleton />
        ) : (
          <div className='flex w-0 min-w-full flex-col gap-2 pr-2.5'>
            {sessions.map((session) => (
              <SessionItem
                key={session.id}
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
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
