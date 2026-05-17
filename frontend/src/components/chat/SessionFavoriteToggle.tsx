"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { sessionService } from "@/services/session-service";
import { useChatStore } from "@/stores/chat-store";

export function SessionFavoriteToggle() {
  const params = useParams();
  const rawSessionId = params?.sessionId;
  const sessionId = Array.isArray(rawSessionId)
    ? rawSessionId[0]
    : (rawSessionId as string | undefined);

  const favoriteFromStore = useChatStore((s) =>
    sessionId ? s.sessionFavorites[sessionId] : undefined,
  );
  const setSessionFavorite = useChatStore((s) => s.setSessionFavorite);
  const bumpSessionListNonce = useChatStore((s) => s.bumpSessionListNonce);
  const [isSaving, setIsSaving] = useState(false);

  const isFavorite = favoriteFromStore === true;
  const tooltip = useMemo(
    () => (isFavorite ? "즐겨찾기 해제" : "즐겨찾기"),
    [isFavorite],
  );

  useEffect(() => {
    if (!sessionId || favoriteFromStore !== undefined) return;

    let cancelled = false;
    sessionService
      .get(sessionId)
      .then((session) => {
        if (!cancelled) setSessionFavorite(sessionId, session.is_favorite);
      })
      .catch(() => {
        // The session list will recover state on the next refresh.
      });

    return () => {
      cancelled = true;
    };
  }, [favoriteFromStore, sessionId, setSessionFavorite]);

  if (!sessionId) return null;

  const handleToggle = async () => {
    const nextFavorite = !isFavorite;
    setSessionFavorite(sessionId, nextFavorite);
    setIsSaving(true);
    try {
      const updated = await sessionService.update(sessionId, {
        is_favorite: nextFavorite,
      });
      setSessionFavorite(sessionId, updated.is_favorite);
      bumpSessionListNonce();
    } catch {
      setSessionFavorite(sessionId, isFavorite);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            className={cn(
              "hidden h-8 w-8 text-fg-muted lg:inline-flex",
              isFavorite && "text-amber-400 hover:text-amber-300",
            )}
            onClick={handleToggle}
            disabled={isSaving}
            aria-label={tooltip}
          >
            <Star
              className="size-4"
              fill={isFavorite ? "currentColor" : "transparent"}
            />
          </Button>
        </TooltipTrigger>
        <TooltipContent>{tooltip}</TooltipContent>
      </Tooltip>
      <Separator
        orientation="vertical"
        className="mx-1 hidden data-[orientation=vertical]:h-5 lg:block"
      />
    </>
  );
}
