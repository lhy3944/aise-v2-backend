"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Spinner } from "@/components/ui/spinner";
import { getMarkdownThemeClassName } from "@/config/markdown-theme";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { usePanelStore } from "@/stores/panel-store";
import { useProjectStore } from "@/stores/project-store";
import { useUiPreferenceStore } from "@/stores/ui-preference-store";
import { FileText, X } from "lucide-react";
import "@/components/ui/ai-elements/css/markdown.css";

interface ChunkPreview {
  document_name: string;
  file_type?: string;
  target: { index: number; content: string };
  before: { index: number; content: string }[];
  after: { index: number; content: string }[];
}

export function SourceViewerPanel() {
  const data = usePanelStore((s) => s.sourceViewerData);
  const closeSourceViewer = usePanelStore((s) => s.closeSourceViewer);
  const projectId = useProjectStore((s) => s.currentProject?.project_id);

  const [preview, setPreview] = useState<ChunkPreview | null>(null);
  const [fetchKey, setFetchKey] = useState<string | null>(null);
  const targetRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  // data가 바뀌면 fetchKey를 갱신하여 loading 파생
  const currentKey = data ? `${data.documentId}:${data.chunkIndex}` : null;
  const loading = currentKey !== null && currentKey !== fetchKey;

  // 문서 유형에 따른 렌더링 분기 (API 응답 우선, panel store fallback)
  const isMarkdown = (preview?.file_type ?? data?.fileType) === "md";

  // 타겟 청크로 자동 스크롤 (ScrollArea viewport 내에서만)
  useEffect(() => {
    if (!preview || !targetRef.current || !viewportRef.current) return;
    const raf = requestAnimationFrame(() => {
      const viewport = viewportRef.current;
      const target = targetRef.current;
      if (!viewport || !target) return;
      const targetRect = target.getBoundingClientRect();
      const viewportRect = viewport.getBoundingClientRect();
      const scrollTo =
        targetRect.top - viewportRect.top + viewport.scrollTop - viewport.clientHeight / 2 + target.clientHeight / 2;
      viewport.scrollTo({ top: Math.max(0, scrollTo), behavior: "smooth" });
    });
    return () => cancelAnimationFrame(raf);
  }, [fetchKey, preview]);

  useEffect(() => {
    if (!projectId || !data) return;

    const key = `${data.documentId}:${data.chunkIndex}`;

    // 같은 청크를 이미 로드했으면 재요청하지 않음
    if (key === fetchKey) return;

    let cancelled = false;

    api
      .get<ChunkPreview>(
        `/api/v1/projects/${projectId}/knowledge/documents/${data.documentId}/chunks/${data.chunkIndex}?context=1`,
      )
      .then((result) => {
        if (!cancelled) {
          setPreview(result);
          setFetchKey(key);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPreview(null);
          setFetchKey(key);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, data, fetchKey]);

  return (
    <div className="flex h-full flex-col">
      {/* 헤더 */}
      <div className="border-line-primary flex items-center gap-2 border-b px-4 py-3">
        <FileText className="text-fg-muted size-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-fg-primary truncate text-sm font-medium">
            {data?.documentName ?? "출처 문서"}
          </p>
          {data && (
            <p className="text-fg-muted text-xs">
              Chunk #{data.chunkIndex} · 출처 [{data.refNumber}]
            </p>
          )}
        </div>
        <button
          onClick={closeSourceViewer}
          className="text-fg-muted hover:text-fg-primary rounded p-1 transition-colors"
          aria-label="닫기"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* 본문 */}
      <ScrollArea viewportRef={viewportRef} className="flex-1 h-full">
        <div className="p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner className="size-6" />
            </div>
          ) : preview ? (
            <div className="space-y-4">
              {preview.before.map((c) => (
                <div key={c.index} className="opacity-40">
                  <ChunkContent content={c.content} isMarkdown={isMarkdown} />
                </div>
              ))}

              {/* 타겟 청크 — 강조 */}
              <div
                ref={targetRef}
                className={cn(
                  "border-accent-primary bg-primary/5 border-l-3 py-3 pl-3",
                )}
              >
                <ChunkContent content={preview.target.content} isMarkdown={isMarkdown} />
              </div>

              {preview.after.map((c) => (
                <div key={c.index} className="opacity-40">
                  <ChunkContent content={c.content} isMarkdown={isMarkdown} />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-fg-muted flex items-center justify-center py-12 text-sm">
              문서를 불러올 수 없습니다.
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function ChunkContent({ content, isMarkdown }: { content: string; isMarkdown: boolean }) {
  const markdownTheme = useUiPreferenceStore((s) => s.markdownTheme);
  const markdownThemeClass = getMarkdownThemeClassName(markdownTheme);

  if (isMarkdown) {
    return (
      <div className={cn("source-markdown text-fg-primary text-sm", markdownThemeClass)}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    );
  }
  return (
    <pre className="text-fg-primary whitespace-pre-wrap break-words text-sm leading-relaxed">
      {content}
    </pre>
  );
}
