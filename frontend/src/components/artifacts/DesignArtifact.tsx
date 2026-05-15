'use client';

import { Boxes, Database, FileText, Sparkles } from 'lucide-react';
import { useCallback, useState } from 'react';

import { DataModelPanel } from '@/components/artifacts/DataModelPanel';
import { SddPanel } from '@/components/artifacts/SddPanel';
import { SystemModelPanel } from '@/components/artifacts/SystemModelPanel';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApiError } from '@/lib/api';
import { designService } from '@/services/design-service';
import { useArtifactActionStore } from '@/stores/artifact-action-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { useArtifactStore, type DesignSubTab } from '@/stores/artifact-store';
import { useProjectStore } from '@/stores/project-store';

const SUB_TABS: Array<{
  value: DesignSubTab;
  label: string;
  icon: typeof Boxes;
}> = [
  { value: 'system_model', label: '시스템 모델', icon: Boxes },
  { value: 'data_model', label: '데이터 모델', icon: Database },
  { value: 'design', label: 'SDD', icon: FileText },
];

export function DesignArtifact() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const projectId = currentProject?.project_id;

  const subTab = useArtifactStore((s) => s.designSubTab);
  const setDesignSubTab = useArtifactStore((s) => s.setDesignSubTab);

  const setGenerating = useArtifactActionStore((s) => s.setGenerating);
  const generating = useArtifactActionStore((s) => s.generating);

  const [pipelineErrors, setPipelineErrors] = useState<string[]>([]);

  const handlePipeline = useCallback(async () => {
    if (!projectId) return;

    setGenerating('system_model', true);
    setGenerating('data_model', true);
    setGenerating('design', true);
    setPipelineErrors([]);

    try {
      const result = await designService.pipeline(projectId);
      setPipelineErrors(result.errors ?? []);
      useArtifactRefreshStore.getState().bump('system_model');
      useArtifactRefreshStore.getState().bump('data_model');
      useArtifactRefreshStore.getState().bump('design');
    } catch (err) {
      if (err instanceof ApiError) {
        setPipelineErrors([err.message]);
      }
    } finally {
      setGenerating('system_model', false);
      setGenerating('data_model', false);
      setGenerating('design', false);
    }
  }, [projectId, setGenerating]);

  if (!projectId) return null;

  const isPipelineRunning =
    generating.system_model || generating.data_model || generating.design;

  return (
    <div className='flex h-full flex-col'>
      {/* Pipeline Header */}
      <div className='border-line-primary flex items-center justify-end gap-2 border-b px-4 py-2'>
        <Button
          size='sm'
          onClick={handlePipeline}
          disabled={isPipelineRunning}
          className='text-xs'
        >
          {isPipelineRunning ? (
            <Spinner size='size-4' />
          ) : (
            <Sparkles className='size-4' />
          )}
          전체 설계 생성
        </Button>
      </div>

      {pipelineErrors.length > 0 && (
        <div className='border-line-primary border-b px-4 py-2 text-xs text-red-500'>
          {pipelineErrors.map((e, i) => (
            <div key={i}>{e}</div>
          ))}
        </div>
      )}

      {/* Sub-tabs */}
      <Tabs
        value={subTab}
        onValueChange={(v) => setDesignSubTab(v as DesignSubTab)}
        className='flex min-h-0 flex-1 flex-col'
      >
        <div className='px-3 pt-1'>
          <TabsList variant='line' className='border-line-subtle w-full'>
            {SUB_TABS.map((tab) => {
              const isGen =
                generating[
                  tab.value === 'design'
                    ? 'design'
                    : (tab.value as 'system_model' | 'data_model')
                ];
              return (
                <TabsTrigger
                  key={tab.value}
                  value={tab.value}
                  className='data-[state=active]:text-accent-primary after:bg-accent-primary gap-1.5 px-3 text-xs'
                >
                  {isGen ? (
                    <Spinner size='size-4' className='text-accent-primary' />
                  ) : (
                    <tab.icon className='size-4' />
                  )}
                  {tab.label}
                </TabsTrigger>
              );
            })}
          </TabsList>
        </div>

        <div className='flex min-h-0 flex-1 flex-col overflow-hidden'>
          <TabsContent value='system_model' className='mt-0 min-h-0 flex-1'>
            <SystemModelPanel />
          </TabsContent>
          <TabsContent value='data_model' className='mt-0 min-h-0 flex-1'>
            <DataModelPanel />
          </TabsContent>
          <TabsContent value='design' className='mt-0 min-h-0 flex-1'>
            <SddPanel />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
