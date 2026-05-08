'use client';

import dynamic from 'next/dynamic';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';
import { artifactService } from '@/services/artifact-service';
import type { DiffFieldEntry, DiffResult } from '@/types/project';
import { useEffect, useMemo, useRef, useState } from 'react';

const MonacoDiffEditor = dynamic(
  () => import('@monaco-editor/react').then((m) => m.DiffEditor),
  {
    ssr: false,
    loading: () => undefined,
  },
);

const TEXT_FIELD_PATTERNS = ['content', 'text'];

function isTextField(path: string): boolean {
  return TEXT_FIELD_PATTERNS.some(
    (p) => path === p || path.startsWith(p + '.'),
  );
}

interface DiffViewerProps {
  headVersionId: string;
  baseVersionId?: string | null;
  onLoadingChange?: (loading: boolean) => void;
}

export function DiffViewer({
  headVersionId,
  baseVersionId,
  onLoadingChange,
}: DiffViewerProps) {
  const [data, setData] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [splitView, setSplitView] = useState(true);
  const [showMeta, setShowMeta] = useState(false);

  // splitView + versionId 조합으로 key 생성 — 뷰 전환/버전 전환 시 리마운트
  const [editorKey, setEditorKey] = useState(
    `${headVersionId}::${baseVersionId ?? ''}::true`,
  );

  const requestKey = `${headVersionId}::${baseVersionId ?? ''}`;
  const keyRef = useRef<string>('');
  const onLoadingChangeRef = useRef(onLoadingChange);

  useEffect(() => {
    onLoadingChangeRef.current = onLoadingChange;
  });

  useEffect(() => {
    let cancelled = false;
    keyRef.current = requestKey;
    queueMicrotask(() => {
      if (cancelled) return;
      setLoading(true);
      setError(null);
      onLoadingChangeRef.current?.(true);
    });

    artifactService
      .diff(headVersionId, baseVersionId ?? undefined)
      .then((res) => {
        if (cancelled || keyRef.current !== requestKey) return;
        setData(res);
        setLoading(false);
        setEditorKey(`${headVersionId}::${baseVersionId ?? ''}::${splitView}`);
        onLoadingChangeRef.current?.(false);
      })
      .catch((err: unknown) => {
        if (cancelled || keyRef.current !== requestKey) return;
        setError(err instanceof Error ? err.message : 'diff 불러오기 실패');
        setLoading(false);
        onLoadingChangeRef.current?.(false);
      });

    return () => {
      cancelled = true;
    };
  }, [headVersionId, baseVersionId, requestKey]);

  const { oldText, newText, metaEntries, metaChangedCount } = useMemo(() => {
    const entries = data?.entries ?? [];
    let oldText = '';
    let newText = '';
    const metaEntries: DiffFieldEntry[] = [];
    let metaChangedCount = 0;

    for (const e of entries) {
      if (isTextField(e.field_path)) {
        if (typeof e.before === 'string') oldText = e.before;
        if (typeof e.after === 'string') newText = e.after;
      } else if (e.kind !== 'unchanged') {
        metaEntries.push(e);
        metaChangedCount += 1;
      }
    }

    return { oldText, newText, metaEntries, metaChangedCount };
  }, [data]);

  const isDark =
    typeof document !== 'undefined' &&
    document.documentElement.classList.contains('dark');

  const hasTextChange = oldText !== newText;

  const handleToggleView = () => {
    const next = !splitView;
    setSplitView(next);
    // 데이터가 이미 있으면 즉시 key 업데이트해서 리마운트
    if (!loading) {
      setEditorKey(`${headVersionId}::${baseVersionId ?? ''}::${next}`);
    }
  };

  if (error) {
    return (
      <div className='text-destructive rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs'>
        {error}
      </div>
    );
  }

  return (
    <div className='flex h-full min-h-0 flex-col gap-3'>
      {/* 툴바 */}
      <div className='text-fg-muted flex shrink-0 items-center gap-3 text-[11px]'>
        {hasTextChange && (
          <Button variant={'outline'} size={'xs'} onClick={handleToggleView}>
            {splitView ? '인라인 뷰' : '나란히 보기'}
          </Button>
        )}
        {!loading && metaChangedCount > 0 && (
          <Button
            variant={'outline'}
            size={'xs'}
            onClick={() => setShowMeta((v) => !v)}
          >
            {showMeta
              ? `메타데이터 숨기기 (${metaChangedCount})`
              : `메타데이터 변경 보기 (${metaChangedCount})`}
          </Button>
        )}
      </div>

      {/* 에디터 */}
      <div className='border-line-primary relative min-h-0 flex-1 overflow-hidden rounded-lg border'>
        {loading && (
          <div className='absolute inset-0 z-10 flex items-center justify-center bg-canvas-primary/70'>
            <Spinner size='size-5' className='text-fg-muted' />
          </div>
        )}
        {!loading && !hasTextChange && (oldText || newText) && (
          <div className='absolute inset-0 z-10 flex items-center justify-center'>
            <p className='text-fg-muted text-xs'>텍스트 변경 없음</p>
          </div>
        )}
        <MonacoDiffEditor
          key={editorKey}
          original={oldText}
          modified={newText}
          language='plaintext'
          theme={isDark ? 'vs-dark' : 'light'}
          loading={false}
          options={{
            readOnly: true,
            renderSideBySide: hasTextChange ? splitView : false,
            renderSideBySideInlineBreakpoint: 0,
            renderOverviewRuler: hasTextChange,
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            lineNumbers: splitView ? 'on' : 'off',
            folding: false,
            minimap: { enabled: false },
            overviewRulerBorder: false,
            hideUnchangedRegions: { enabled: hasTextChange },
            scrollbar: {
              verticalScrollbarSize: 6,
              horizontalScrollbarSize: 6,
            },
            fontSize: 12,
            lineHeight: 22,
            padding: { top: 8 },
            diffCodeLens: false,
            renderMarginRevertIcon: false,
          }}
        />
      </div>

      {/* 메타데이터 변경 */}
      {showMeta && metaEntries.length > 0 && (
        <div className='border-line-primary shrink-0 rounded-md border p-3'>
          <div className='text-fg-muted mb-2 text-[11px] font-medium'>
            메타데이터 변경
          </div>
          <div className='flex flex-col gap-1.5'>
            {metaEntries.map((entry) => (
              <MetaDiffRow key={entry.field_path} entry={entry} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const META_LABELS: Record<string, string> = {
  section_id: '섹션',
  source_document_id: '출처 문서',
  source_location: '출처 위치',
  confidence_score: '신뢰도',
  is_auto_extracted: '추출 방식',
  order_index: '정렬 순서',
  metadata: '메타데이터',
};

function MetaDiffRow({ entry }: { entry: DiffFieldEntry }) {
  const label = META_LABELS[entry.field_path] ?? entry.field_path;
  const kindLabel =
    entry.kind === 'added'
      ? '추가'
      : entry.kind === 'removed'
        ? '삭제'
        : entry.kind === 'modified'
          ? '변경'
          : '';
  const kindCls =
    entry.kind === 'added'
      ? 'text-emerald-600'
      : entry.kind === 'removed'
        ? 'text-red-500'
        : 'text-amber-600';

  return (
    <div className='text-fg-muted flex items-center gap-2 text-[11px]'>
      <span className='text-fg-secondary font-medium'>{label}</span>
      <span className={cn('text-[10px] font-medium uppercase', kindCls)}>
        {kindLabel}
      </span>
      {entry.kind === 'modified' && (
        <span className='flex items-center gap-1'>
          <span className='text-red-500/80 line-through'>
            {formatMetaValue(entry.before)}
          </span>
          <span className='text-fg-muted'>&rarr;</span>
          <span className='text-emerald-600'>
            {formatMetaValue(entry.after)}
          </span>
        </span>
      )}
      {entry.kind === 'added' && (
        <span className='text-emerald-600'>{formatMetaValue(entry.after)}</span>
      )}
      {entry.kind === 'removed' && (
        <span className='text-red-500/80 line-through'>
          {formatMetaValue(entry.before)}
        </span>
      )}
    </div>
  );
}

function formatMetaValue(v: unknown): string {
  if (v === null || v === undefined) return '(빈 값)';
  if (typeof v === 'string') return v.length > 0 ? v : '(빈 문자열)';
  if (typeof v === 'number' || typeof v === 'boolean') return String(v);
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}
