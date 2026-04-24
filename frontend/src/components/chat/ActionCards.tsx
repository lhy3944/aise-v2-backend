'use client';

import { cn } from '@/lib/utils';
import { streamExtractArtifactRecords } from '@/services/artifact-record-service';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { usePanelStore, LayoutMode } from '@/stores/panel-store';
import { useProjectStore } from '@/stores/project-store';
import { useReadinessStore } from '@/stores/readiness-store';
import { BookOpen, Database, FileText, Loader2, RefreshCw } from 'lucide-react';
import { useCallback } from 'react';

interface ActionCardsProps {
  onAction: (action: string) => void;
}

interface ActionContext {
  isReady: boolean;
}

export function ActionCards({ onAction }: ActionCardsProps) {
  const currentProject = useProjectStore((s) => s.currentProject);
  const readiness = useReadinessStore((s) => s.data);
  const extracting = useArtifactRecordStore((s) => s.extracting);
  const setExtracting = useArtifactRecordStore((s) => s.setExtracting);
  const setCandidates = useArtifactRecordStore((s) => s.setCandidates);
  const setExtractError = useArtifactRecordStore((s) => s.setExtractError);
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const setRightPanelPreset = usePanelStore((s) => s.setRightPanelPreset);

  const ctx: ActionContext = {
    isReady: readiness?.is_ready ?? false,
  };

  const handleExtractRecords = useCallback(() => {
    if (!currentProject || extracting) return;

    setExtracting(true);
    onAction('레코드 추출을 시작합니다...');

    streamExtractArtifactRecords(currentProject.project_id, undefined, {
      onDone: (candidates) => {
        setCandidates(candidates);
        // Records 탭으로 전환 + 우패널 열기
        setActiveTab('records');
        setRightPanelPreset(LayoutMode.SPLIT);
      },
      onError: (msg) => {
        setExtractError(msg);
        onAction(`레코드 추출 실패: ${msg}`);
      },
    });
  }, [currentProject, extracting, onAction, setExtracting, setCandidates, setExtractError, setActiveTab, setRightPanelPreset]);

  if (!currentProject) return null;

  const cards = [
    {
      id: 'extract',
      icon: extracting ? Loader2 : Database,
      title: extracting ? '추출 중...' : '레코드 추출',
      description: extracting
        ? '지식 문서를 분석하고 있습니다'
        : '지식 문서에서 섹션별 레코드를 추출합니다',
      enabled: ctx.isReady && !extracting,
      disabledReason: '프로젝트 준비가 필요합니다 (지식/용어/섹션)',
      onClick: handleExtractRecords,
      spinning: extracting,
    },
    {
      id: 'srs',
      icon: FileText,
      title: 'SRS 문서 생성',
      description: '승인된 레코드로 SRS 문서를 생성합니다',
      enabled: false, // TODO: hasRecords
      disabledReason: '먼저 레코드를 추출해주세요',
      onClick: () => onAction('SRS 문서 생성을 시작해주세요.'),
    },
    {
      id: 'glossary-review',
      icon: BookOpen,
      title: '용어집 검토',
      description: '미승인 용어를 검토하고 승인합니다',
      enabled: false,
      disabledReason: '미승인 용어가 없습니다',
      onClick: () => onAction('미승인 용어를 검토해주세요.'),
    },
    {
      id: 'srs-regenerate',
      icon: RefreshCw,
      title: 'SRS 재생성',
      description: '수정된 레코드로 SRS를 다시 생성합니다',
      enabled: false,
      disabledReason: '기존 SRS가 없습니다',
      onClick: () => onAction('SRS 문서를 재생성해주세요.'),
    },
  ];

  return (
    <div className='grid grid-cols-2 gap-3'>
      {cards.map((card) => (
        <button
          key={card.id}
          onClick={card.onClick}
          disabled={!card.enabled}
          className={cn(
            'flex items-start gap-3 rounded-lg border p-4 text-left transition-all',
            card.enabled
              ? 'border-line-primary hover:border-accent-primary/50 hover:bg-canvas-surface/50 cursor-pointer'
              : 'border-line-primary/50 cursor-not-allowed opacity-50',
          )}
        >
          <div
            className={cn(
              'flex size-9 shrink-0 items-center justify-center rounded-md',
              card.enabled
                ? 'bg-accent-primary/10 text-accent-primary'
                : 'bg-canvas-surface text-fg-muted',
            )}
          >
            <card.icon className={cn('size-4', card.spinning && 'animate-spin')} />
          </div>
          <div className='min-w-0'>
            <p className='text-fg-primary text-sm font-medium'>{card.title}</p>
            <p className='text-fg-muted mt-0.5 text-xs'>
              {card.enabled ? card.description : card.disabledReason}
            </p>
          </div>
        </button>
      ))}
    </div>
  );
}
