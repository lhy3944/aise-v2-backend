import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export enum LayoutMode {
  WIDE = 'wide',
  SPLIT = 'split',
  CLOSED = 'closed',
  CUSTOM = 'custom',
}

export type RightPanelView = 'artifacts' | 'source-viewer';

export interface SourceViewerData {
  documentId: string;
  documentName: string;
  chunkIndex: number;
  refNumber: number;
  fileType?: string;
}

interface PanelState {
  leftSidebarOpen: boolean;
  rightPanelOpen: boolean;
  rightPanelWidth: number;
  layoutMode: LayoutMode;
  rightPanelView: RightPanelView;
  sourceViewerData: SourceViewerData | null;
  notificationOpen: boolean;
  fullWidthMode: boolean;
  isMobile: boolean;
  isTablet: boolean;
  previousLeftSidebar: boolean;

  toggleLeftSidebar: () => void;
  toggleRightPanel: () => void;
  setRightPanelWidth: (pct: number) => void;
  setRightPanelPreset: (preset: LayoutMode.WIDE | LayoutMode.SPLIT | LayoutMode.CLOSED) => void;
  openSourceViewer: (data: SourceViewerData) => void;
  closeSourceViewer: () => void;
  resetRightPanelView: () => void;
  toggleNotification: () => void;
  toggleFullWidth: () => void;
  setViewport: (width: number) => void;
}

export const usePanelStore = create<PanelState>()(
  persist(
    (set, get) => ({
      leftSidebarOpen: false,
      rightPanelOpen: false,
      rightPanelWidth: 0,
      layoutMode: LayoutMode.CLOSED,
      rightPanelView: 'artifacts' as RightPanelView,
      sourceViewerData: null as SourceViewerData | null,
      notificationOpen: false,
      fullWidthMode: false,
      isMobile: false,
      isTablet: false,
      previousLeftSidebar: false,

      toggleLeftSidebar: () => {
        set((s) => ({ leftSidebarOpen: !s.leftSidebarOpen }));
      },

      toggleRightPanel: () => {
        set((s) => ({ rightPanelOpen: !s.rightPanelOpen }));
      },

      setRightPanelWidth: (pct) => {
        const clamped = Math.max(20, Math.min(70, pct));
        set({ rightPanelWidth: clamped });
      },

      openSourceViewer: (data) => {
        const s = get();
        set({
          rightPanelView: 'source-viewer',
          sourceViewerData: data,
          rightPanelOpen: true,
          // 패널이 닫혀있었으면 SPLIT으로 열기
          ...(s.rightPanelOpen ? {} : { rightPanelWidth: 50, layoutMode: LayoutMode.SPLIT }),
        });
      },

      closeSourceViewer: () => {
        set({ rightPanelView: 'artifacts', sourceViewerData: null });
      },

      // 오른쪽 패널 위에 떠 있는 오버레이 뷰어들(출처 뷰어 등)만 닫고 기본 artifacts 패널로 복귀.
      // 새 뷰어 추가 시 여기서 해당 상태 초기화를 함께 관리한다.
      resetRightPanelView: () => {
        set({ rightPanelView: 'artifacts', sourceViewerData: null });
      },

      setRightPanelPreset: (preset) => {
        switch (preset) {
          case LayoutMode.WIDE:
            set({
              rightPanelOpen: true,
              rightPanelWidth: 70,
              layoutMode: LayoutMode.WIDE,
            });
            break;
          case LayoutMode.SPLIT:
            set({
              rightPanelOpen: true,
              rightPanelWidth: 50,
              layoutMode: LayoutMode.SPLIT,
            });
            break;
          case LayoutMode.CLOSED:
            set({ rightPanelOpen: false, layoutMode: LayoutMode.CLOSED, rightPanelView: 'artifacts', sourceViewerData: null });
            break;
        }
      },

      toggleNotification: () => {
        set((s) => ({
          notificationOpen: !s.notificationOpen,
        }));
      },

      toggleFullWidth: () => {
        set((s) => ({ fullWidthMode: !s.fullWidthMode }));
      },

      setViewport: (width) => {
        const isMobile = width < 768;
        const isTablet = width >= 768 && width < 1024;
        const state = get();

        // Only adjust sidebar state when the viewport category actually changes
        const wasMobile = state.isMobile;
        const wasTablet = state.isTablet;
        const wasDesktop = !wasMobile && !wasTablet;
        const isDesktop = !isMobile && !isTablet;

        if (isMobile && !wasMobile) {
          set({
            isMobile: true,
            isTablet: false,
            previousLeftSidebar: state.leftSidebarOpen || state.previousLeftSidebar,
            leftSidebarOpen: false,
            rightPanelOpen: false,
            notificationOpen: false,
          });
        } else if (isTablet && !wasTablet) {
          set({
            isMobile: false,
            isTablet: true,
            previousLeftSidebar: state.leftSidebarOpen || state.previousLeftSidebar,
            leftSidebarOpen: false,
          });
        } else if (isDesktop && !wasDesktop) {
          set({
            isMobile: false,
            isTablet: false,
            leftSidebarOpen: state.previousLeftSidebar,
            previousLeftSidebar: false,
          });
        }
      },
    }),
    {
      name: 'aise-panel',
      partialize: (state) => ({
        leftSidebarOpen: state.leftSidebarOpen,
        rightPanelOpen: state.rightPanelOpen,
        rightPanelWidth: state.rightPanelWidth,
        layoutMode: state.layoutMode,
        fullWidthMode: state.fullWidthMode,
      }),
    },
  ),
);
