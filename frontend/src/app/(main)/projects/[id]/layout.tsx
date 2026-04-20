'use client';

import { ProjectGlossaryTab } from '@/components/projects/ProjectGlossaryTab';
import { ProjectKnowledgeTab } from '@/components/projects/ProjectKnowledgeTab';
import { ProjectOverviewTab } from '@/components/projects/ProjectOverviewTab';
import { ProjectSectionsTab } from '@/components/projects/ProjectSectionsTab';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { layoutMaxWNormal } from '@/config/layout';
import { cn } from '@/lib/utils';
import { projectService } from '@/services/project-service';
import { usePanelStore } from '@/stores/panel-store';
import { useProjectStore } from '@/stores/project-store';
import {
  ArrowLeft,
  BookOpen,
  Box,
  FolderOpen,
  LayoutList,
  MessageSquareMore,
} from 'lucide-react';
import Link from 'next/link';
import { use, useEffect } from 'react';

interface Props {
  params: Promise<{ id: string }>;
}

const TABS = [
  { value: 'overview', icon: Box, label: '기본 정보', shortLabel: '정보' },
  {
    value: 'knowledge',
    icon: FolderOpen,
    label: '지식 저장소',
    shortLabel: '지식',
  },
  { value: 'glossary', icon: BookOpen, label: '용어 사전', shortLabel: '용어' },
  { value: 'sections', icon: LayoutList, label: '섹션', shortLabel: '섹션' },
];

export default function ProjectDetailLayout({ params }: Props) {
  const { id } = use(params);
  const fullWidthMode = usePanelStore((s) => s.fullWidthMode);
  const currentProject = useProjectStore((s) => s.currentProject);
  const projects = useProjectStore((s) => s.projects);
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject);

  // currentProject가 없거나 id가 다르면 projects 배열에서 찾거나 API fetch
  useEffect(() => {
    if (currentProject?.project_id === id) return;

    const found = projects.find((p) => p.project_id === id);
    if (found) {
      setCurrentProject(found);
      return;
    }

    projectService
      .get(id)
      .then(setCurrentProject)
      .catch(() => {});
  }, [id, currentProject?.project_id, projects, setCurrentProject]);

  const projectName =
    currentProject?.project_id === id ? currentProject.name : null;
  const maxW = layoutMaxWNormal(fullWidthMode);

  return (
    <Tabs
      defaultValue='overview'
      className='flex flex-1 flex-col overflow-hidden'
    >
      {/* Tab Navigation */}
      <div className='bg-canvas-primary'>
        <div
          className={cn(
            'mx-auto transition-[max-width] duration-300 ease-in-out sm:px-6',
            maxW,
          )}
        >
          <div className='flex items-center gap-2.5 pt-6 pb-1 max-sm:px-4'>
            <Button variant='outline' size='icon-sm' className='size-7' asChild>
              <Link href='/projects' aria-label='프로젝트 목록으로'>
                <ArrowLeft className='size-4' />
              </Link>
            </Button>

            <Badge variant='ghost'>
              {projectName && (
                <span className='text-fg-secondary truncate text-xs font-medium'>
                  {projectName}
                </span>
              )}
            </Badge>

            <Button
              variant='outline'
              className='ml-auto gap-1.5 py-3.5! px-7!'
              asChild
              size={'xs'}
            >
              <Link href='/agent'>
                <MessageSquareMore />
                <span className='text-xs'>에이전트 대화</span>
              </Link>
            </Button>
          </div>
          <TabsList
            variant='line'
            className='border-line-subtle w-full justify-start border-b'
          >
            {TABS.map(({ value, icon: Icon, label, shortLabel }) => (
              <TabsTrigger
                key={value}
                value={value}
                className='data-[state=active]:text-accent-primary after:bg-accent-primary shrink-0 gap-1.5 px-3 md:px-5'
              >
                <Icon className='size-4' />
                <span className='md:hidden'>{shortLabel}</span>
                <span className='hidden md:inline'>{label}</span>
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
      </div>

      {/* Content */}
      <div className='flex-1 overflow-y-auto'>
        <div
          className={cn(
            'mx-auto px-4 py-6 transition-[max-width] duration-300 ease-in-out sm:px-6',
            maxW,
          )}
        >
          <TabsContent value='overview'>
            <ProjectOverviewTab projectId={id} />
          </TabsContent>
          <TabsContent value='knowledge'>
            <ProjectKnowledgeTab projectId={id} />
          </TabsContent>
          <TabsContent value='glossary'>
            <ProjectGlossaryTab projectId={id} />
          </TabsContent>
          <TabsContent value='sections'>
            <ProjectSectionsTab projectId={id} />
          </TabsContent>
        </div>
      </div>
    </Tabs>
  );
}
