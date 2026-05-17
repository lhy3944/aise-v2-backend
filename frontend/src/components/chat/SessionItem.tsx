"use client";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Spinner } from "@/components/ui/spinner";
import { useOverlay } from "@/hooks/useOverlay";
import { cn } from "@/lib/utils";
import type { SessionResponse } from "@/services/session-service";
import {
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Share2,
  Star,
  Trash2,
} from "lucide-react";
import { memo, useState } from "react";

interface SessionItemProps {
  session: SessionResponse;
  isActive: boolean;
  isStreaming?: boolean;
  onClick: () => void;
  onDelete?: () => void;
  onRename?: (title: string) => void;
  onFavoriteToggle?: (isFavorite: boolean) => void;
}

export const SessionItem = memo(function SessionItem({
  session,
  isActive,
  isStreaming = false,
  onClick,
  onDelete,
  onRename,
  onFavoriteToggle,
}: SessionItemProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const overlay = useOverlay();

  const handleRename = () => {
    overlay.prompt({
      title: "세션 이름 변경",
      label: "새 이름",
      placeholder: "새 이름을 입력하세요",
      defaultValue: session.title,
      requiredMessage: "이름을 입력하세요",
      maxLength: 100,
      confirmLabel: "변경",
      onConfirm: (value) => {
        if (value !== session.title) onRename?.(value);
      },
    });
  };

  return (
    <div
      className={cn(
        "group relative flex w-full min-w-0 items-center overflow-hidden pr-2 transition-colors",
        isActive
          ? "bg-canvas-surface-2 text-fg-primary"
          : "text-fg-secondary hover:bg-canvas-surface-2",
      )}
    >
      {isActive && (
        <div className="absolute top-0 left-0 h-full w-[3px] bg-accent-primary" />
      )}
      <button
        onClick={onClick}
        className="flex min-w-0 flex-1 items-center justify-start gap-2 px-2.5 py-2"
      >
        {isStreaming ? (
          <Spinner
            size="size-3.5"
            className="shrink-0 text-accent-primary"
            aria-label="응답 생성 중"
          />
        ) : session.is_favorite ? (
          <Star
            className="h-3.5 w-3.5 shrink-0 text-amber-400"
            fill="currentColor"
          />
        ) : (
          <MessageSquare className="h-3.5 w-3.5 shrink-0" fill="currentColor" />
        )}
        <span className="min-w-0 truncate text-[13px]">{session.title}</span>
      </button>

      <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
        <DropdownMenuTrigger asChild>
          <button
            onClick={(e) => e.stopPropagation()}
            className={cn(
              "shrink-0 cursor-pointer rounded p-1 text-fg-secondary transition-opacity hover:text-fg-primary",
              menuOpen ? "opacity-100" : "opacity-0 group-hover:opacity-100",
            )}
            aria-label="세션 메뉴"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" side="right" className="w-40">
          <DropdownMenuItem
            className="gap-2 text-xs"
            onClick={() => onFavoriteToggle?.(!session.is_favorite)}
          >
            <Star
              className={cn(
                "h-3.5 w-3.5",
                session.is_favorite && "text-amber-400",
              )}
              fill={session.is_favorite ? "currentColor" : "transparent"}
            />
            {session.is_favorite ? "즐겨찾기 해제" : "즐겨찾기"}
          </DropdownMenuItem>
          <DropdownMenuItem className="gap-2 text-xs" onClick={handleRename}>
            <Pencil className="h-3.5 w-3.5" />
            이름 변경
          </DropdownMenuItem>
          <DropdownMenuItem className="gap-2 text-xs">
            <Share2 className="h-3.5 w-3.5" />
            공유
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="gap-2 text-xs text-destructive focus:text-destructive"
            onClick={(e) => {
              e.stopPropagation();
              onDelete?.();
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
            삭제
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
});
