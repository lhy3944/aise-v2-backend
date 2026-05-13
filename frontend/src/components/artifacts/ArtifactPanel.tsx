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
import { useArtifactActionStore } from '@/stores/artifact-action-store';
import type { ArtifactType } from '@/stores/artifact-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { useProjectStore } from '@/stores/project-store';
import type { ArtifactKind } from '@/types/agent-events';
import {
  Database,
  FileText,
  FlaskConical,
  InspectionPanel,
  Layers,
} from 'lucide-react';

const ARTIFACT_TABS: Array<{
  value: ArtifactType;
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

const STALE_TAB_MAP: Record<string, ArtifactType[]> = {
  srs: ['srs'],
  system_model: ['design'],
  data_model: ['design'],
  design: ['design'],
  testcase: ['testcase'],
  record: ['records'],
};

export function ArtifactPanel() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const activeTab = useArtifactStore((s) => s.activeTab);
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const generating = useArtifactActionStore((s) => s.generating);
  const overlay = useOverlay();

  const { stale: staleList } = useImpact(currentProject?.project_id ?? null);

  // 현재 활성 탭에 해당하는 stale 항목 필터링
  const activeTabStale = staleList.filter((s) =>
    (STALE_TAB_MAP[s.artifact_type] ?? []).includes(activeTab),
  );

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
          onApplyComplete={() => overlay.closeModal()}
        />
      ),
    });
  };

  if (!currentProject) {
    return (
      <div className='flex h-full items-center justify-center p-6'>
        <div className='text-center'>
          <Layers className='text-fg-muted mx-auto mb-3 size-10' />
          <p className='text-fg-secondary text-sm font-medium'>
            프로젝트를 선택해주세요
          </p>
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
      <div className='relative min-w-0 pt-2'>
        <ScrollArea className='w-full'>
          <div className='pb-2.5'>
            <TabsList
              variant='line'
              className='border-line-subtle w-max min-w-full border-b'
            >
              {ARTIFACT_TABS.map((tab) => {
                const isGenerating =
                  tab.kind === 'design'
                    ? generating.design ||
                      generating.system_model ||
                      generating.data_model
                    : tab.kind
                      ? generating[tab.kind]
                      : false;
                const tabStale = staleList.filter((s) =>
                  (STALE_TAB_MAP[s.artifact_type] ?? []).includes(tab.value),
                );
                return (
                  <TabsTrigger
                    key={tab.value}
                    value={tab.value}
                    className='data-[state=active]:text-accent-primary after:bg-accent-primary gap-1.5 px-3 text-xs whitespace-nowrap'
                  >
                    {isGenerating ? (
                      <Spinner size='size-4' className='text-accent-primary' />
                    ) : (
                      <tab.icon className='size-4' />
                    )}
                    {tab.label}
                    {tabStale.length > 0 && (
                      <span className='bg-amber-500 size-2 rounded-full' />
                    )}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>
          <ScrollBar orientation='horizontal' className='h-0.5' />
        </ScrollArea>
        <div className='from-canvas-surface pointer-events-none absolute inset-y-0 left-0 w-4 bg-linear-to-r to-transparent hidden lg:hidden max-lg:block' />
        <div className='from-canvas-surface pointer-events-none absolute inset-y-0 right-0 w-8 bg-linear-to-l to-transparent hidden lg:hidden max-lg:block' />
      </div>

      {/* Stale Banner — 활성 탭에 stale이 있으면 탭바 아래에 배너 표시 */}
      {activeTabStale.length > 0 && (
        <div className='border-line-primary bg-amber-500 flex shrink-0 items-center gap-2 border-b px-4 py-1.5 mx-0.5'>
          <span className='text-white text-xs'>
            {activeTabStale.length}개 산출물이 변경점 영향 분석이 필요합니다.
          </span>
          <Button
            variant='ghost'
            size='sm'
            className='text-white hover:bg-amber-600 hover:text-white ml-auto h-6 gap-1 px-2 text-xs'
            onClick={openImpactModal}
          >
            <InspectionPanel className='size-4' />
            분석
          </Button>
        </div>
      )}

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
