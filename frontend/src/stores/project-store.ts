import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Project } from '@/types/project';

type ViewMode = 'card' | 'list';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  viewMode: ViewMode;
  isLoading: boolean;
  error: string | null;

  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  setViewMode: (mode: ViewMode) => void;
  addProject: (project: Project) => void;
  updateProject: (project: Project) => void;
  removeProject: (projectId: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      projects: [],
      currentProject: null,
      viewMode: 'card',
      isLoading: false,
      error: null,

      setProjects: (projects) => set({ projects }),
      setCurrentProject: (project) => set({ currentProject: project }),
      setViewMode: (viewMode) => set({ viewMode }),
      addProject: (project) => set((s) => ({ projects: [project, ...s.projects] })),
      updateProject: (project) =>
        set((s) => ({
          projects: s.projects.map((p) => (p.project_id === project.project_id ? project : p)),
          currentProject:
            s.currentProject?.project_id === project.project_id ? project : s.currentProject,
        })),
      removeProject: (projectId) =>
        set((s) => ({
          projects: s.projects.filter((p) => p.project_id !== projectId),
          currentProject: s.currentProject?.project_id === projectId ? null : s.currentProject,
        })),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
    }),
    {
      name: 'aise-project',
      partialize: (s) => ({ currentProject: s.currentProject, viewMode: s.viewMode }),
    },
  ),
);
