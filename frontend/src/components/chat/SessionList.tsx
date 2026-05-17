"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Check,
  CirclePlus,
  ListFilterPlus,
  RefreshCw,
  Star,
} from "lucide-react";
import { SessionItem } from "@/components/chat/SessionItem";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { sessionService, type SessionSortBy } from "@/services/session-service";
import type { SessionResponse } from "@/services/session-service";
import { useChatStore } from "@/stores/chat-store";
import { useHitlStore } from "@/stores/hitl-store";
import { useProjectStore } from "@/stores/project-store";

const SKELETON_WIDTHS = [72, 58, 85, 63, 91, 54, 78, 67];

const SORT_OPTIONS: Array<{
  value: SessionSortBy;
  label: string;
  icon: typeof CirclePlus;
}> = [
  { value: "created", label: "생성됨", icon: CirclePlus },
  { value: "updated", label: "업데이트됨", icon: RefreshCw },
];

function SessionListSkeleton() {
  return (
    <div className="flex flex-col gap-1.5 px-1">
      {SKELETON_WIDTHS.map((width, i) => (
        <div key={i} className="flex items-center gap-2 px-2.5 py-2">
          <Skeleton className="h-3.5 w-3.5 shrink-0 rounded" />
          <Skeleton className="h-3.5 rounded" style={{ width: `${width}%` }} />
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
  const streamingSessionIds = useChatStore((s) => s.streamingSessionIds);
  const setSessionFavorites = useChatStore((s) => s.setSessionFavorites);
  const setSessionFavorite = useChatStore((s) => s.setSessionFavorite);
  const openHitlForSession = useHitlStore((s) => s.openForSession);
  const clearHitlSession = useHitlStore((s) => s.clearSession);

  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFetchingMore, setIsFetchingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SessionSortBy>("updated");
  const [favoriteFirst, setFavoriteFirst] = useState(false);
  const projectIdRef = useRef(currentProject?.project_id);

  const viewportRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  const rememberFavorites = useCallback(
    (items: SessionResponse[]) => {
      setSessionFavorites(
        Object.fromEntries(items.map((item) => [item.id, item.is_favorite])),
      );
    },
    [setSessionFavorites],
  );

  const fetchSessions = useCallback(async () => {
    if (!currentProject) {
      setSessions([]);
      setIsLoading(false);
      setNextCursor(null);
      return;
    }
    try {
      setIsLoading(true);
      const res = await sessionService.list(
        currentProject.project_id,
        undefined,
        {
          sortBy,
          favoriteFirst,
        },
      );
      setSessions(res.sessions);
      rememberFavorites(res.sessions);
      setNextCursor(res.next_cursor);
    } catch {
      setSessions([]);
      setNextCursor(null);
    } finally {
      setIsLoading(false);
    }
  }, [currentProject, sortBy, favoriteFirst, rememberFavorites]);

  useEffect(() => {
    const currentId = currentProject?.project_id;
    if (currentId !== projectIdRef.current) {
      projectIdRef.current = currentId;
      setSessions([]);
      setNextCursor(null);
    }
    void Promise.resolve().then(fetchSessions);
  }, [currentProject?.project_id, fetchSessions, sessionListNonce]);

  const fetchMore = useCallback(async () => {
    if (!currentProject || !nextCursor || isFetchingMore) return;
    try {
      setIsFetchingMore(true);
      const res = await sessionService.list(
        currentProject.project_id,
        nextCursor,
        {
          sortBy,
          favoriteFirst,
        },
      );
      setSessions((prev) => [...prev, ...res.sessions]);
      rememberFavorites(res.sessions);
      setNextCursor(res.next_cursor);
    } catch {
      // Keep the cursor so the next intersection can retry.
    } finally {
      setIsFetchingMore(false);
    }
  }, [
    currentProject,
    nextCursor,
    isFetchingMore,
    sortBy,
    favoriteFirst,
    rememberFavorites,
  ]);

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
      { root: viewport, rootMargin: "200px", threshold: 0 },
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
          router.push("/agent");
        }
      } catch {
        // Ignore menu-level failures for now.
      }
    },
    [activeSessionId, clearHitlSession, router],
  );

  const handleRename = useCallback(
    async (sessionId: string, newTitle: string) => {
      try {
        await sessionService.update(sessionId, { title: newTitle });
        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s)),
        );
      } catch {
        // Ignore menu-level failures for now.
      }
    },
    [],
  );

  const handleFavoriteToggle = useCallback(
    async (sessionId: string, isFavorite: boolean) => {
      try {
        const updated = await sessionService.update(sessionId, {
          is_favorite: isFavorite,
        });
        setSessionFavorite(sessionId, updated.is_favorite);
        setSessions((prev) =>
          prev.map((session) =>
            session.id === sessionId
              ? { ...session, is_favorite: updated.is_favorite }
              : session,
          ),
        );
        if (favoriteFirst) void fetchSessions();
      } catch {
        // Ignore menu-level failures for now.
      }
    },
    [favoriteFirst, fetchSessions, setSessionFavorite],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center justify-between px-2 pb-2">
        <h3 className="text-xs font-medium text-fg-muted">모든 작업</h3>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              aria-label="세션 정렬"
              className={cn(
                "cursor-pointer rounded-md p-1.5 text-icon-default transition-colors hover:bg-canvas-secondary hover:text-icon-active",
                favoriteFirst && "text-icon-active",
              )}
            >
              <ListFilterPlus className="size-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuLabel className="text-xs text-fg-muted">
              정렬
            </DropdownMenuLabel>
            {SORT_OPTIONS.map(({ value, label, icon: Icon }) => (
              <DropdownMenuItem
                key={value}
                className="gap-2 text-sm"
                onSelect={(event) => event.preventDefault()}
                onClick={() => setSortBy(value)}
              >
                <Icon className="size-4" />
                <span className="flex-1">{label}</span>
                {sortBy === value && <Check className="size-4" />}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="gap-2 text-sm"
              onSelect={(event) => event.preventDefault()}
              onClick={() => setFavoriteFirst((prev) => !prev)}
            >
              <Star className="size-4 text-amber-400" />
              <span className="flex-1">즐겨찾기 고정</span>
              {favoriteFirst && <Check className="size-4" />}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {isLoading ? (
        <SessionListSkeleton />
      ) : (
        <ScrollArea viewportRef={viewportRef} className="min-h-0 flex-1">
          {sessions.map((session) => (
            <div key={session.id} className="mb-px">
              <SessionItem
                session={session}
                isActive={session.id === activeSessionId}
                isStreaming={streamingSessionIds.has(session.id)}
                onClick={() => {
                  openHitlForSession(session.id);
                  router.push(`/agent/${session.id}`);
                  onSessionSelect?.();
                }}
                onDelete={() => handleDelete(session.id)}
                onRename={(title) => handleRename(session.id, title)}
                onFavoriteToggle={(next) =>
                  handleFavoriteToggle(session.id, next)
                }
              />
            </div>
          ))}

          {nextCursor && !isFetchingMore && (
            <div ref={sentinelRef} className="h-1" />
          )}

          {isFetchingMore && (
            <div className="flex items-center justify-center gap-2 py-3">
              <Spinner size="size-3.5" className="text-fg-muted" />
            </div>
          )}
        </ScrollArea>
      )}
    </div>
  );
}
