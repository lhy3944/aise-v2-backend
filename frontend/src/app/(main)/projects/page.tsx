'use client';

import { ConfirmDialog } from '@/components/overlay/ConfirmDialog';
import { Modal } from '@/components/overlay/Modal';
import { ProjectCard } from '@/components/projects/ProjectCard';
import {
  ProjectCreateForm,
  ProjectCreateFormActions,
} from '@/components/projects/ProjectCreateForm';
import { ProjectListItem } from '@/components/projects/ProjectListItem';
import { ProjectListSkeleton } from '@/components/projects/ProjectListSkeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { layoutMaxW } from '@/config/layout';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/utils';
import { projectService } from '@/services/project-service';
import { usePanelStore } from '@/stores/panel-store';
import { useProjectStore } from '@/stores/project-store';
import type { ProjectCreate } from '@/types/project';
import { Grid2X2, Plus, Search, TextAlignJustify } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

export default function ProjectsPage() {
  const {
    projects,
    setProjects,
    addProject,
    removeProject,
    isLoading,
    setLoading,
    setError,
  } = useProjectStore();
  const viewMode = useProjectStore((s) => s.viewMode);
  const setViewMode = useProjectStore((s) => s.setViewMode);
  const fullWidthMode = usePanelStore((s) => s.fullWidthMode);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const filteredProjects = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return projects;
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.description?.toLowerCase().includes(query) ||
        p.domain?.toLowerCase().includes(query),
    );
  }, [projects, search]);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    const minDelay = new Promise((r) => setTimeout(r, 400));
    try {
      const [data] = await Promise.all([projectService.list(), minDelay]);
      setProjects(data.projects);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : '프로젝트 목록을 불러올 수 없습니다.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [setProjects, setLoading, setError]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  async function confirmDelete() {
    if (!deleteTarget) return;
    try {
      await projectService.delete(deleteTarget);
      removeProject(deleteTarget);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : '프로젝트 삭제에 실패했습니다.';
      setError(message);
    } finally {
      setDeleteTarget(null);
    }
  }

  async function handleCreate(data: ProjectCreate) {
    setCreating(true);
    try {
      const project = await projectService.create(data);
      addProject(project);
      setCreateOpen(false);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : '프로젝트 생성에 실패했습니다.';
      setError(message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className='flex-1 overflow-y-auto'>
      <div
        className={cn(
          'mx-auto p-6 transition-[max-width] duration-300 ease-in-out',
          layoutMaxW(fullWidthMode),
        )}
      >
        {/* Header */}
        <div className='border-line-subtle mb-6 flex items-center justify-between gap-3 border-b pb-6'>
          <div className='group/search border-line-primary focus-within:border-accent-primary flex w-80 rounded-xs border transition-colors'>
            <Input
              placeholder='프로젝트 검색'
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') setSearch(searchInput);
              }}
              disabled={projects.length === 0}
              className='border-0 focus-visible:border-0 focus-visible:ring-0'
            />
            <Button
              variant='outline'
              size='icon'
              onClick={() => setSearch(searchInput)}
              aria-label='검색'
              disabled={projects.length === 0}
              className='text-fg-muted shrink-0 rounded-l-none rounded-r-xs border-0 border-l'
            >
              <Search className='size-4' />
            </Button>
          </div>

          <div className='flex gap-3'>
            <div className='border-line-primary flex h-9 items-center rounded-xs border'>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={viewMode === 'card' ? 'secondary' : 'ghost'}
                    size='icon-sm'
                    onClick={() => setViewMode('card')}
                    aria-label='카드 뷰'
                    className='h-full rounded-l-xs rounded-r-none border-0'
                  >
                    <Grid2X2 />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>카드 보기</TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={viewMode === 'list' ? 'secondary' : 'ghost'}
                    size='icon-sm'
                    onClick={() => setViewMode('list')}
                    aria-label='리스트 뷰'
                    className='h-full rounded-l-none rounded-r-xs border-0'
                  >
                    <TextAlignJustify />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>리스트 보기</TooltipContent>
              </Tooltip>
            </div>

            <Button onClick={() => setCreateOpen(true)} variant={'outline'}>
              <Plus />
              프로젝트 생성
            </Button>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <ProjectListSkeleton />
        ) : filteredProjects.length === 0 ? (
          search ? (
            <div className='animate-in fade-in flex min-h-[calc(100vh-14rem)] flex-col items-center justify-center text-center duration-300'>
              <div className='bg-canvas-surface mb-4 flex size-16 items-center justify-center rounded-full'>
                <Search className='text-fg-muted size-6' />
              </div>
              <h2 className='text-fg-primary text-base font-medium'>
                검색 결과가 없습니다
              </h2>
              <p className='text-fg-secondary text-sm'>
                다른 검색어로 시도해 보세요.
              </p>
            </div>
          ) : (
            <div className='animate-in fade-in flex min-h-[calc(100vh-14rem)] items-center justify-center'>
              <Button
                variant={'ghost'}
                onClick={() => setCreateOpen(true)}
                className='border-line-primary hover:border-fg-muted hover:bg-canvas-surface/50 pointer-events-auto flex h-3/12 min-h-56 w-sm max-w-2xl cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed text-center transition-colors'
              >
                <div className='bg-canvas-surface mb-4 flex size-16 items-center justify-center rounded-full'>
                  <Plus className='text-fg-muted size-6' />
                </div>
                <h2 className='text-fg-primary text-base font-medium'>
                  프로젝트가 없습니다
                </h2>
                <p className='text-fg-secondary text-sm'>
                  새 프로젝트를 만들어 시작하세요.
                </p>
              </Button>
            </div>
          )
        ) : viewMode === 'card' ? (
          <div className='animate-in fade-in grid gap-4 duration-300 sm:grid-cols-2 lg:grid-cols-3'>
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.project_id}
                project={project}
                onDelete={(id) => setDeleteTarget(id)}
              />
            ))}
          </div>
        ) : (
          <div className='animate-in fade-in flex flex-col gap-2 duration-300'>
            {filteredProjects.map((project) => (
              <ProjectListItem
                key={project.project_id}
                project={project}
                onDelete={(id) => setDeleteTarget(id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirm */}
      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title='프로젝트 삭제'
        description='이 프로젝트를 삭제하시겠습니까? 관련된 모든 데이터가 영구적으로 삭제됩니다.'
        confirmLabel='삭제'
        variant='destructive'
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Create Modal */}
      <Modal
        open={createOpen}
        onOpenChange={setCreateOpen}
        title='프로젝트 생성'
        description='프로젝트 정보를 입력하고 사용할 모듈을 선택하세요.'
        size='lg'
        footer={
          <ProjectCreateFormActions
            onCancel={() => setCreateOpen(false)}
            isLoading={creating}
          />
        }
      >
        <ProjectCreateForm onSubmit={handleCreate} />
      </Modal>
    </div>
  );
}
