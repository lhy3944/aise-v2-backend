'use client';

import { ArtifactRecordsPanel } from '@/components/artifacts/ArtifactRecordsPanel';
import { DesignArtifact } from '@/components/artifacts/DesignArtifact';
import { SrsArtifact } from '@/components/artifacts/SrsArtifact';
import { TestCaseArtifact } from '@/components/artifacts/TestCaseArtifact';
import { ImpactPanel } from '@/components/artifacts/workspace/ImpactPanel';
import { Button } from '@/components/ui/button';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Spinner } from '@/components/ui/spinner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useImpact } from '@/hooks/useImpact';
import { useOverlay } from '@/hooks/useOverlay';
import type { ArtifactType } from '@/stores/artifact-store';
import { useArtifactActionStore } from '@/stores/artifact-action-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { useProjectStore } from '@/stores/project-store';
import type { ArtifactKind } from '@/types/agent-events';
import {
  AlertTriangle,
  Database,
  FileText,
  FlaskConical,
  Layers,
} from 'lucide-react';

const ARTIFACT_TABS: Array<{
  value: ArtifactType;
  /** action store 의 generating[kind] 와 매핑되는 키. records 는 자동 생성 액션이 없어 null. */
  kind: ArtifactKind | null;
  label: string;
  icon: typeof Database;
}> = [
  { value: 'records', kind: null, label: 'Records', icon: Database },
  { value: 'srs', kind: 'srs', label: 'SRS', icon: FileText },
  { value: 'design', kind: 'design', label: 'Design', icon: Layers },
  {
    value: 'testcase',
    kind: 'testcase',
    label: 'Test Cases',
    icon: FlaskConical,
  },
];

export function ArtifactPanel() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const activeTab = useArtifactStore((s) => s.activeTab);
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const generating = useArtifactActionStore((s) => s.generating);
  const overlay = useOverlay();

  // 영향도(stale) — 1건 이상이면 탭바 옆에 알림 버튼.
  const { stale: staleList } = useImpact(currentProject?.project_id ?? null);

  const openImpactModal = () => {
    if (!currentProject) return;
    const projectId = currentProject.project_id;
    overlay.modal({
      title: '영향도 분석',
      description:
        '입력 변경으로 인해 갱신이 필요한 산출물입니다. 선택한 항목을 자동 재생성할 수 있습니다.',
      size: 'lg',
      content: (
        <ImpactPanel
          projectId={projectId}
          onClose={() => overlay.closeModal()}
        />
      ),
    });
  };

  if (!currentProject) {
    return (
      <div className='flex h-full items-center justify-center p-6'>
        <div className='text-center'>
          <Layers className='text-fg-muted mx-auto mb-3 size-10' />
          <p className='text-fg-secondary text-sm font-medium'>프로젝트를 선택해주세요</p>
          <p className='text-fg-muted mt-1 text-xs'>
            왼쪽 사이드바에서 프로젝트를 선택하면 산출물을 확인할 수 있습니다.
          </p>
        </div>
      </div>
    );
  }

  return (
    <Tabs
      value={activeTab}
      onValueChange={(v) => setActiveTab(v as ArtifactType)}
      className='flex h-full flex-col'
    >
      {/* Tab Bar */}
      <div className='flex shrink-0 items-end gap-2 px-2 pt-2'>
        <div className='relative min-w-0 flex-1'>
          <ScrollArea className='w-full px-2'>
            <div className='pb-2.5'>
              <TabsList
                variant='line'
                className='border-line-subtle w-max min-w-full'
              >
                {ARTIFACT_TABS.map((tab) => {
                  const isGenerating = tab.kind ? generating[tab.kind] : false;
                  return (
                    <TabsTrigger
                      key={tab.value}
                      value={tab.value}
                      className='data-[state=active]:text-accent-primary after:bg-accent-primary gap-1.5 px-3 text-xs whitespace-nowrap'
                    >
                      {isGenerating ? (
                        <Spinner
                          size='size-3.5'
                          className='text-accent-primary'
                        />
                      ) : (
                        <tab.icon className='size-3.5' />
                      )}
                      {tab.label}
                    </TabsTrigger>
                  );
                })}
              </TabsList>
            </div>
            <ScrollBar orientation='horizontal' className='h-0.5' />
          </ScrollArea>
          <div className='from-background pointer-events-none absolute inset-y-0 left-0 w-4 bg-linear-to-r to-transparent' />
          <div className='from-background pointer-events-none absolute inset-y-0 right-0 w-8 bg-linear-to-l to-transparent' />
        </div>
        {staleList.length > 0 && (
          <Button
            variant='ghost'
            size='sm'
            className='mb-2 h-7 shrink-0 gap-1.5 border border-amber-500/40 bg-amber-500/10 px-2 text-[11px] font-medium text-amber-700 hover:bg-amber-500/20 dark:text-amber-400'
            onClick={openImpactModal}
            title='영향도 분석 — 자동 재생성'
          >
            <AlertTriangle className='size-3.5' />
            stale {staleList.length}
          </Button>
        )}
      </div>

      {/* Content */}
      <div className='flex min-h-0 flex-1 flex-col'>
        <TabsContent value='records' className='mt-0 h-full'>
          <ArtifactRecordsPanel projectId={currentProject.project_id} />
        </TabsContent>
        <TabsContent value='srs' className='mt-0 h-full'>
          <SrsArtifact />
        </TabsContent>
        <TabsContent value='design' className='mt-0 h-full'>
          <DesignArtifact />
        </TabsContent>
        <TabsContent value='testcase' className='mt-0 h-full'>
          <TestCaseArtifact />
        </TabsContent>
      </div>
    </Tabs>
  );
}
