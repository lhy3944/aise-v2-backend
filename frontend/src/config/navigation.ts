import type { LucideIcon } from 'lucide-react';
import { Box, CircleHelp, MessageSquareMore, SlidersHorizontal } from 'lucide-react';

export const headerTabsConfig = [
  { href: '/agent', label: 'Agent', icon: MessageSquareMore },
  // { href: "/workflow", label: "Workflow", icon: Workflow },
  { href: '/projects', label: 'Projects', icon: Box },
];

export interface SidebarAction {
  id: 'settings' | 'project' | 'help';
  label: string;
  icon: LucideIcon;
}

export const SIDEBAR_ACTIONS: SidebarAction[] = [
  { id: 'settings', label: '앱 설정', icon: SlidersHorizontal },
  { id: 'project', label: '프로젝트', icon: Box },
  { id: 'help', label: '도움말', icon: CircleHelp },
];
