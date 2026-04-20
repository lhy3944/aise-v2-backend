import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  DEFAULT_CHAT_FONT_SIZE,
  type ChatFontSize,
} from '@/config/chat-font-size';
import {
  DEFAULT_MARKDOWN_THEME,
  type MarkdownThemePreset,
} from '@/config/markdown-theme';

interface UiPreferenceState {
  markdownTheme: MarkdownThemePreset;
  chatFontSize: ChatFontSize;
  setMarkdownTheme: (theme: MarkdownThemePreset) => void;
  setChatFontSize: (size: ChatFontSize) => void;
}

export const useUiPreferenceStore = create<UiPreferenceState>()(
  persist(
    (set) => ({
      markdownTheme: DEFAULT_MARKDOWN_THEME,
      chatFontSize: DEFAULT_CHAT_FONT_SIZE,
      setMarkdownTheme: (markdownTheme) => set({ markdownTheme }),
      setChatFontSize: (chatFontSize) => set({ chatFontSize }),
    }),
    {
      name: 'aise-ui-preferences',
      partialize: (s) => ({
        markdownTheme: s.markdownTheme,
        chatFontSize: s.chatFontSize,
      }),
    },
  ),
);
