'use client';

import { Boxes, Database, Link2, RefreshCw, Sparkles } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ArtifactEmptyGuide } from '@/components/artifacts/ArtifactEmptyGuide';
import { PlantUmlDiagram } from '@/components/shared/PlantUmlDiagram';
import { MessageResponse } from '@/components/ui/ai-elements/message';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import { useOverlay } from '@/hooks/useOverlay';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/utils';
import { dataModelService } from '@/services/data-model-service';
import { useArtifactActionStore } from '@/stores/artifact-action-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { useProjectStore } from '@/stores/project-store';
import type { DataModelDocument, DataModelSection } from '@/types/project';

const STATUS_LABEL: Record<string, { label: string; tone: string }> = {
  completed: { label: '완료', tone: 'bg-green-600 text-white' },
  generating: { label: '생성중', tone: 'bg-amber-600 text-white' },
  failed: { label: '실패', tone: 'bg-red-600 text-white' },
};

const EMPTY_DM_GUIDES = [
  {
    icon: Boxes,
    title: '시스템 모델 기반',
    description: '시스템 모델의 엔티티를 기반으로 데이터 모델을 생성합니다.',
  },
  {
    icon: Database,
    title: '3단계 모델링',
    description: '개념/논리/물리 데이터 모델을 자동 생성합니다.',
  },
];

function StatusChip({ status }: { status: string }) {
  const cfg = STATUS_LABEL[status] ?? {
    label: status,
    tone: 'bg-canvas-primary text-fg-muted',
  };
  return (
    <span
      className={cn(
        'rounded px-2 py-0.5 text-[10px] font-medium whitespace-nowrap',
        cfg.tone,
      )}
    >
      {cfg.label}
    </span>
  );
}

function formatCreatedAt(value: string) {
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return value;
  }
}

export function DataModelPanel() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const projectId = currentProject?.project_id;

  const [documents, setDocuments] = useState<DataModelDocument[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const generating = useArtifactActionStore((s) => s.generating.data_model);
  const setGenerating = useArtifactActionStore((s) => s.setGenerating);

  const refreshNonce = useArtifactRefreshStore.getState().nonce;

  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const setDesignSubTab = useArtifactStore((s) => s.setDesignSubTab);
  const setPendingFocus = useArtifactStore((s) => s.setPendingFocus);

  const selectedDoc = useMemo(
    () => documents.find((d) => d.data_model_id === selectedId) ?? null,
    [documents, selectedId],
  );

  const fetchList = useCallback(
    async (preferId?: string) => {
      if (!projectId) return;
      try {
        const res = await dataModelService.list(projectId);
        const sorted = [...res.documents].sort((a, b) => b.version - a.version);
        setDocuments(sorted);
        setSelectedId((prev) => {
          if (preferId && sorted.some((d) => d.data_model_id === preferId)) {
            return preferId;
          }
          if (prev && sorted.some((d) => d.data_model_id === prev)) return prev;
          return sorted[0]?.data_model_id ?? null;
        });
      } finally {
        setLoading(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    dataModelService
      .list(projectId)
      .then((res) => {
        if (cancelled) return;
        const sorted = [...res.documents].sort((a, b) => b.version - a.version);
        setDocuments(sorted);
        setSelectedId((prev) => {
          if (sorted.length > 0 && sorted[0].data_model_id !== prev)
            return sorted[0].data_model_id;
          if (prev && sorted.some((d) => d.data_model_id === prev)) return prev;
          return sorted[0]?.data_model_id ?? null;
        });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, refreshNonce]);

  const handleGenerate = useCallback(async () => {
    if (!projectId) return;
    setGenerating('data_model', true);
    setErrorMessage(null);
    try {
      const doc = await dataModelService.generate(projectId);
      await fetchList(doc.data_model_id);
      useArtifactRefreshStore.getState().bump('data_model');
    } catch (err) {
      if (err instanceof ApiError) setErrorMessage(err.message);
    } finally {
      setGenerating('data_model', false);
    }
  }, [projectId, fetchList, setGenerating]);

  if (!projectId) return null;

  if (loading) {
    return (
      <div className='flex h-full items-center justify-center'>
        <Spinner size='size-6' className='text-fg-muted' />
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <ArtifactEmptyGuide
        icon={Database}
        title='데이터 모델이 존재하지 않습니다.'
        description='SRS와 시스템 모델 기반으로 데이터 모델 초안을 생성합니다.'
        guides={EMPTY_DM_GUIDES}
        errorMessage={errorMessage}
        action={
          <Button
            size='sm'
            onClick={handleGenerate}
            disabled={generating}
            className='h-8 gap-1.5 px-3 text-xs'
          >
            {generating ? (
              <Spinner size='size-4' />
            ) : (
              <Sparkles className='size-4' />
            )}
            데이터 모델 생성
          </Button>
        }
      />
    );
  }

  return (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='border-line-primary flex flex-col gap-2 border-b px-4 py-2 md:flex-row md:items-center md:justify-between'>
        <div className='flex min-w-0 items-center gap-2'>
          <Select
            value={selectedId ?? undefined}
            onValueChange={(v) => setSelectedId(v)}
          >
            <SelectTrigger
              size='sm'
              className='h-7 w-full gap-2 text-xs md:w-auto md:min-w-[220px]'
            >
              <SelectValue placeholder='버전 선택'>
                {selectedDoc && (
                  <span className='flex items-center gap-2'>
                    <StatusChip status={selectedDoc.status} />
                    <span className='text-fg-primary font-medium'>
                      v{selectedDoc.version}
                    </span>
                    <span className='text-fg-muted whitespace-nowrap'>
                      {formatCreatedAt(selectedDoc.created_at)}
                    </span>
                  </span>
                )}
              </SelectValue>
            </SelectTrigger>
            <SelectContent position='popper' side='bottom' align='start'>
              {documents.map((doc) => (
                <SelectItem
                  key={doc.data_model_id}
                  value={doc.data_model_id}
                  className='text-xs'
                >
                  <span className='flex w-full items-center gap-2'>
                    <StatusChip status={doc.status} />
                    <span className='text-fg-primary font-medium'>
                      v{doc.version}
                    </span>
                    <span className='text-fg-muted whitespace-nowrap'>
                      {formatCreatedAt(doc.created_at)}
                    </span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className='flex items-center justify-end gap-1.5'>
          {selectedDoc?.based_on_srs?.version_id && (
            <Button
              variant='ghost'
              size='sm'
              className='h-7 gap-1.5 text-xs'
              onClick={() => {
                setPendingFocus({
                  kind: 'srs',
                  versionId: selectedDoc!.based_on_srs!.version_id!,
                });
                setActiveTab('srs');
              }}
            >
              <Link2 className='size-4' />
              SRS 출처
            </Button>
          )}
          {selectedDoc?.based_on_system_model?.version_id && (
            <Button
              variant='ghost'
              size='sm'
              className='h-7 gap-1.5 text-xs'
              onClick={() => {
                setDesignSubTab('system_model');
              }}
            >
              <Link2 className='size-4' />
              시스템 모델 출처
            </Button>
          )}
          <Button
            variant='ghost'
            size='sm'
            className='h-7 gap-1.5 text-xs'
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? (
              <Spinner size='size-4' />
            ) : (
              <RefreshCw className='size-4' />
            )}
            재생성
          </Button>
        </div>
      </div>

      {/* Body */}
      {selectedDoc && selectedDoc.status === 'failed' && (
        <div className='border-line-primary border-b px-4 py-2 text-xs text-red-500'>
          생성 실패: {selectedDoc.error_message ?? '알 수 없는 오류'}
        </div>
      )}

      <ScrollArea className='min-h-0 flex-1'>
        <div className='flex flex-col gap-4 p-4 pb-6'>
          {selectedDoc ? (
            selectedDoc.sections.map((section, idx) => (
              <section
                key={section.section_id ?? `idx-${idx}`}
                className='border-line-primary rounded-lg border'
              >
                <header className='bg-canvas-surface mb-2 rounded-t-lg px-4 py-3'>
                  <h3 className='text-fg-primary text-sm font-semibold'>
                    {section.title}
                  </h3>
                </header>
                {section.content ? (
                  <PlantUmlDiagram className='px-4 pb-4 text-sm' content={section.content} />
                ) : (
                  <p className='text-fg-muted px-4 pb-4 text-xs italic'>내용 없음</p>
                )}
              </section>
            ))
          ) : (
            <p className='text-fg-muted text-center text-xs'>
              섹션이 없습니다.
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
