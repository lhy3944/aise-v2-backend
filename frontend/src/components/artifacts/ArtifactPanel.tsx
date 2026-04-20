'use client';

import { DesignArtifact } from '@/components/artifacts/DesignArtifact';
import { RecordsArtifact } from '@/components/artifacts/RecordsArtifact';
import { SrsArtifact } from '@/components/artifacts/SrsArtifact';
import { TestCaseArtifact } from '@/components/artifacts/TestCaseArtifact';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { ArtifactType } from '@/stores/artifact-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { useProjectStore } from '@/stores/project-store';
import { Database, FileText, FlaskConical, Layers } from 'lucide-react';

const ARTIFACT_TABS = [
  { value: 'records' as const, label: 'Records', icon: Database },
  { value: 'srs' as const, label: 'SRS', icon: FileText },
  { value: 'design' as const, label: 'Design', icon: Layers },
  { value: 'testcase' as const, label: 'Test Cases', icon: FlaskConical },
];

export function ArtifactPanel() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const activeTab = useArtifactStore((s) => s.activeTab);
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);

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
      <div className='shrink-0 px-2 pt-2'>
        <div className='relative'>
          <ScrollArea className='w-full px-2'>
            <div className='pb-2.5'>
              <TabsList
                variant='line'
                className='border-line-subtle w-max min-w-full'
              >
                {ARTIFACT_TABS.map((tab) => (
                  <TabsTrigger
                    key={tab.value}
                    value={tab.value}
                    className='data-[state=active]:text-accent-primary after:bg-accent-primary gap-1.5 px-3 text-xs whitespace-nowrap'
                  >
                    <tab.icon className='size-3.5' />
                    {tab.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
            <ScrollBar orientation='horizontal' className='h-0.5' />
          </ScrollArea>
          <div className='from-background pointer-events-none absolute inset-y-0 left-0 w-4 bg-linear-to-r to-transparent' />
          <div className='from-background pointer-events-none absolute inset-y-0 right-0 w-8 bg-linear-to-l to-transparent' />
        </div>
      </div>

      {/* Content */}
      <div className='flex min-h-0 flex-1 flex-col'>
        <TabsContent value='records' className='mt-0 h-full'>
          <RecordsArtifact projectId={currentProject.project_id} />
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
