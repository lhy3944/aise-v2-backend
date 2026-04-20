import type { ProjectModule } from '@/types/project';

export const MODULE_LABELS: Record<ProjectModule, string> = {
  requirements: 'Requirements',
  design: 'Design',
  testcase: 'Test Case',
};

export const MODULE_COLORS: Record<ProjectModule, string> = {
  requirements: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 px-4',
  design: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 px-4',
  testcase: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-4',
};
