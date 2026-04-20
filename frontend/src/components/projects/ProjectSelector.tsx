"use client";

import { Modal } from "@/components/overlay/Modal";
import {
  ProjectCreateForm,
  ProjectCreateFormActions,
} from "@/components/projects/ProjectCreateForm";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api";
import { showToast } from "@/lib/toast";
import { cn } from "@/lib/utils";
import { projectService } from "@/services/project-service";
import { useProjectStore } from "@/stores/project-store";
import type { Project, ProjectCreate } from "@/types/project";
import { Box, Check, ChevronsUpDown, Plus, Settings } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

interface ProjectSelectorProps {
  collapsed?: boolean;
}

export function ProjectSelector({ collapsed = false }: ProjectSelectorProps) {
  const projects = useProjectStore((s) => s.projects);
  const currentProject = useProjectStore((s) => s.currentProject);
  const setProjects = useProjectStore((s) => s.setProjects);
  const addProject = useProjectStore((s) => s.addProject);
  const setCurrentProject = useProjectStore((s) => s.setCurrentProject);
  const [open, setOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      const data = await projectService.list();
      setProjects(data.projects);
    } catch {
      // silently fail — projects page will handle errors
    }
  }, [setProjects]);

  useEffect(() => {
    if (projects.length === 0) {
      fetchProjects();
    }
  }, [projects.length, fetchProjects]);

  function handleSelect(project: Project) {
    setCurrentProject(project);
    setOpen(false);
  }

  async function handleCreate(data: ProjectCreate) {
    setCreating(true);
    try {
      const project = await projectService.create(data);
      addProject(project);
      setCurrentProject(project);
      setCreateOpen(false);
      showToast.success(`${project.name} 프로젝트가 생성되었습니다.`);
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.message : "프로젝트 생성에 실패했습니다.";
      showToast.error(msg);
    } finally {
      setCreating(false);
    }
  }

  function handleOpenCreate() {
    setCreateOpen(true);
  }

  if (collapsed) {
    return (
      <>
        <DropdownMenu open={open} onOpenChange={setOpen}>
          <Tooltip>
            <TooltipTrigger asChild>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-9 w-9",
                    currentProject
                      ? "text-accent-primary"
                      : "text-icon-default hover:text-icon-active",
                  )}
                >
                  <Box className="size-5" />
                </Button>
              </DropdownMenuTrigger>
            </TooltipTrigger>
            <TooltipContent side="right">
              {currentProject ? currentProject.name : "프로젝트 선택"}
            </TooltipContent>
          </Tooltip>
          <DropdownMenuContent side="right" align="start" className="w-52">
            <ProjectDropdownItems
              projects={projects}
              currentProject={currentProject}
              onSelect={handleSelect}
              onOpenCreate={handleOpenCreate}
            />
          </DropdownMenuContent>
        </DropdownMenu>
        <CreateProjectDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          onSubmit={handleCreate}
          isLoading={creating}
        />
      </>
    );
  }

  return (
    <>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger asChild>
          <button
            className={cn(
              "border-line-primary hover:bg-canvas-surface flex w-full items-center gap-2 rounded-md border px-2.5 py-2 text-left transition-colors",
              open && "bg-canvas-surface",
            )}
          >
            <Box
              className={cn(
                "size-4 shrink-0",
                currentProject ? "text-accent-primary" : "text-fg-muted",
              )}
            />
            <span
              className={cn(
                "flex-1 truncate text-xs font-medium",
                currentProject ? "text-fg-primary" : "text-fg-muted",
              )}
            >
              {currentProject?.name ?? "프로젝트 선택"}
            </span>
            <ChevronsUpDown className="text-fg-muted size-3.5 shrink-0" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="start"
          style={{ minWidth: "var(--radix-dropdown-menu-trigger-width)" }}
        >
          <ProjectDropdownItems
            projects={projects}
            currentProject={currentProject}
            onSelect={handleSelect}
            onOpenCreate={handleOpenCreate}
          />
        </DropdownMenuContent>
      </DropdownMenu>
      <CreateProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onSubmit={handleCreate}
        isLoading={creating}
      />
    </>
  );
}

function ProjectDropdownItems({
  projects,
  currentProject,
  onSelect,
  onOpenCreate,
}: {
  projects: Project[];
  currentProject: Project | null;
  onSelect: (project: Project) => void;
  onOpenCreate: () => void;
}) {
  const router = useRouter();

  if (projects.length === 0) {
    return (
      <div className="px-3 py-4 text-center">
        <Button
          variant="ghost"
          size="sm"
          className="w-full gap-1.5 text-xs"
          onClick={onOpenCreate}
        >
          <Plus className="size-3" fill="currentColor" />
          프로젝트 생성
        </Button>
      </div>
    );
  }

  return (
    <>
      <ScrollArea className="max-h-48">
        {projects.map((project) => {
          const isSelected = currentProject?.project_id === project.project_id;
          return (
            <DropdownMenuItem
              key={project.project_id}
              onClick={() => onSelect(project)}
              className={cn(
                "gap-2 text-xs",
                isSelected && "text-accent-primary",
              )}
            >
              <Check
                className={cn(
                  "size-3 shrink-0",
                  isSelected ? "opacity-100" : "opacity-0",
                )}
              />
              <span className="flex-1 truncate">{project.name}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  router.push(`/projects/${project.project_id}`);
                }}
                className="text-fg-muted hover:text-fg-primary -mr-1 flex size-5 shrink-0 items-center justify-center rounded transition-colors"
              >
                <Settings className="size-4" />
              </button>
            </DropdownMenuItem>
          );
        })}
      </ScrollArea>
      <DropdownMenuSeparator />
      <div className="flex items-center justify-center gap-1">
        <Button variant="outline" className="w-full" onClick={onOpenCreate}>
          <Plus className="size-4" />
          <span className="text-xs">프로젝트 생성</span>
        </Button>
      </div>
    </>
  );
}

function CreateProjectDialog({
  open,
  onOpenChange,
  onSubmit,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: ProjectCreate) => void;
  isLoading: boolean;
}) {
  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="프로젝트 생성"
      description="프로젝트 정보를 입력하고 사용할 모듈을 선택하세요."
      size="2xl"
      footer={
        <ProjectCreateFormActions
          onCancel={() => onOpenChange(false)}
          isLoading={isLoading}
        />
      }
    >
      <ProjectCreateForm onSubmit={onSubmit} />
    </Modal>
  );
}
