"use client";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useProjectStore } from "@/stores/project-store";
import { useSuggestionStore } from "@/stores/suggestion-store";
import { CornerRightUp, LightbulbIcon, RefreshCwIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";

interface PromptCard {
  title: string;
  description: string;
}

const FALLBACK_CARDS: PromptCard[] = [
  {
    title: "문서 분석",
    description: "업로드된 문서의 주요 내용을 요약해주세요",
  },
  {
    title: "요구사항 추출",
    description: "지식 문서에서 요구사항 레코드를 추출해주세요",
  },
  {
    title: "프로젝트 현황",
    description: "현재 프로젝트의 요구사항 정의 상태를 분석해주세요",
  },
  {
    title: "요구사항 작성 도움",
    description: "새로운 기능 요구사항을 작성하는 것을 도와주세요",
  },
];

const CARDS_PER_ROW = 2;

/** 카드 수를 짝수로 맞춤 (2개씩 노출하므로 홀수면 마지막 카드 제거) */
const ensureEven = (cards: PromptCard[]): PromptCard[] =>
  cards.length % 2 === 0 ? cards : cards.slice(0, -1);
const AUTO_SLIDE_INTERVAL = 5000;

interface PromptSuggestionsProps {
  rows?: number;
  onSelect?: (prompt: string) => void;
}

export function PromptSuggestions({
  rows = 2,
  onSelect,
}: PromptSuggestionsProps) {
  const currentProject = useProjectStore((s) => s.currentProject);
  const projectId = currentProject?.project_id;

  const getCached = useSuggestionStore((s) => s.getCached);
  const setCache = useSuggestionStore((s) => s.setCache);

  // 로컬 캐시에서 즉시 로드
  const [cards, setCards] = useState<PromptCard[]>(() => {
    if (!projectId) return [];
    const cached = getCached(projectId);
    return cached ? cached.cards : [];
  });
  const [loading, setLoading] = useState(() => !cards.length);

  // 프로젝트 변경 시 캐시 확인
  const prevProjectIdRef = useRef(projectId);
  if (prevProjectIdRef.current !== projectId) {
    prevProjectIdRef.current = projectId;
    if (projectId) {
      const cached = getCached(projectId);
      if (cached) {
        if (cards !== cached.cards) setCards(cached.cards);
        if (loading) setLoading(false);
      } else {
        if (cards.length) setCards([]);
        if (!loading) setLoading(true);
      }
    }
  }

  // fingerprint 비교 → 변경 시에만 전체 fetch
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;

    const cached = useSuggestionStore.getState().getCached(projectId);

    async function sync() {
      try {
        // 1) fingerprint만 가볍게 조회
        const { fingerprint } = await api.get<{ fingerprint: string }>(
          `/api/v1/projects/${projectId}/prompt-suggestions/fingerprint`,
        );
        if (cancelled) return;

        // 2) 로컬 캐시와 fingerprint 비교 — 같으면 스킵
        if (cached && cached.fingerprint === fingerprint) {
          if (!cards.length) setCards(cached.cards);
          setLoading(false);
          return;
        }

        // 3) 변경됨 → 전체 suggestions fetch
        const res = await api.get<{
          fingerprint: string;
          suggestions: PromptCard[];
        }>(`/api/v1/projects/${projectId}/prompt-suggestions`);
        if (cancelled) return;

        const raw =
          res.suggestions.length > 0 ? res.suggestions : FALLBACK_CARDS;
        const data = ensureEven(raw);
        setCache(projectId!, res.fingerprint, data);
        setCards(data);
        setLoading(false);
      } catch {
        if (cancelled) return;
        // API 실패 시 캐시가 있으면 유지, 없으면 fallback
        if (cached) {
          setCards(cached.cards);
        } else {
          setCards(FALLBACK_CARDS);
        }
        setLoading(false);
      }
    }

    sync();
    return () => {
      cancelled = true;
    };
  }, [projectId, setCache]); // eslint-disable-line react-hooks/exhaustive-deps

  const count = rows * CARDS_PER_ROW;
  const totalPages = Math.max(1, Math.ceil(cards.length / count));

  const [page, setPage] = useState(0);
  const [direction, setDirection] = useState(1);

  const visibleCards = cards.slice(page * count, page * count + count);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startTimer = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (totalPages <= 1) return;
    timerRef.current = setInterval(() => {
      setPage((prev) => (prev + 1) % totalPages);
    }, AUTO_SLIDE_INTERVAL);
  }, [totalPages]);

  const goNext = useCallback(() => {
    if (totalPages <= 1) return;
    setDirection(1);
    setPage((prev) => (prev + 1) % totalPages);
    startTimer();
  }, [totalPages, startTimer]);

  const handleShuffle = useCallback(() => {
    goNext();
  }, [goNext]);

  useEffect(() => {
    startTimer();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [startTimer]);

  // 프로젝트 미선택이면 표시하지 않음
  if (!projectId) {
    return null;
  }

  // 로딩 스켈레톤
  if (loading) {
    return (
      <div className="mt-10 space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-muted-foreground flex items-center gap-1.5 text-sm">
            <LightbulbIcon
              className="size-5 text-red-500"
              fill="currentColor"
            />
            <span>질문을 준비하는 중...</span>
          </div>
          <Skeleton className="h-7 w-16 rounded-lg" />
        </div>
        <div className="grid grid-cols-2 gap-2">
          {Array.from({ length: count }).map((_, i) => (
            <Skeleton key={i} className="h-[72px] rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (cards.length === 0) return null;

  return (
    <div className="mt-10 space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-muted-foreground flex items-center gap-1.5 text-sm">
          <LightbulbIcon className="size-5 text-red-500" fill="currentColor" />
          <span>이런 질문을 시도해 보세요</span>
        </div>
        {totalPages > 1 && (
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground h-7 gap-1 text-xs"
            onClick={handleShuffle}
          >
            <RefreshCwIcon className="size-4" />
            전환
          </Button>
        )}
      </div>

      <div className="overflow-hidden">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.div
            key={page}
            className="grid grid-cols-2 gap-2"
            initial={{ x: direction * 10, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: direction * -10, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            {visibleCards.map((card) => (
              <Button
                key={card.title}
                variant="ghost"
                className="group border-border hover:bg-accent relative h-full w-full overflow-hidden flex-col items-start justify-start rounded-lg border p-3 text-left whitespace-normal transition-colors"
                onClick={() => onSelect?.(card.description)}
              >
                <CornerRightUp className="text-muted-foreground absolute top-2.5 right-2.5 size-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                <div className="min-w-0 w-full">
                  <p className="text-sm font-semibold truncate">{card.title}</p>
                  <p className="text-muted-foreground mt-1 line-clamp-2 break-all text-xs/6">
                    {card.description}
                  </p>
                </div>
              </Button>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
