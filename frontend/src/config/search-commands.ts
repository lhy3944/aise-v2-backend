import type { LucideIcon } from 'lucide-react';
import {
  Box,
  LayoutDashboard,
  MessageSquare,
  MessageSquareMore,
  Moon,
  Plus,
} from 'lucide-react';

export interface SearchNavigationItem {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  keywords: string[];
}

export interface SearchActionItem {
  id: string;
  label: string;
  icon: LucideIcon;
  keywords: string[];
  href?: string;
  actionId?: string;
}

export const SEARCH_NAVIGATION_ITEMS: SearchNavigationItem[] = [
  {
    id: 'nav-agent',
    label: 'Agent',
    icon: MessageSquareMore,
    href: '/agent',
    keywords: ['에이전트', '채팅', 'chat', 'AI'],
  },
  {
    id: 'nav-projects',
    label: 'Projects',
    icon: Box,
    href: '/projects',
    keywords: ['프로젝트', '목록', 'list'],
  },
  {
    id: 'nav-dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    href: '/dashboard',
    keywords: ['대시보드', '현황'],
  },
];

export const SEARCH_ACTION_ITEMS: SearchActionItem[] = [
  {
    id: 'action-new-project',
    label: '새 프로젝트 만들기',
    icon: Plus,
    href: '/projects',
    keywords: ['create', 'new', '생성', '추가'],
  },
  {
    id: 'action-new-chat',
    label: '새 채팅 시작',
    icon: MessageSquare,
    href: '/agent',
    keywords: ['chat', '대화', '새로운'],
  },
  {
    id: 'action-toggle-theme',
    label: '테마 변경',
    icon: Moon,
    actionId: 'toggle-theme',
    keywords: ['dark', 'light', '다크', '라이트', '모드', 'theme'],
  },
];
