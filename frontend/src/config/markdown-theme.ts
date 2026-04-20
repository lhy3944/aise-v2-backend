export const MARKDOWN_THEME_OPTIONS = [
  {
    value: 'docs',
    label: 'Docs',
    description: '가독성 중심의 문서형 스타일',
  },
  {
    value: 'github',
    label: 'GitHub',
    description: '중립적인 GitHub 스타일',
  },
  {
    value: 'dense',
    label: 'Dense',
    description: '요구사항 표에 최적화된 압축 스타일',
  },
] as const;

export type MarkdownThemePreset = (typeof MARKDOWN_THEME_OPTIONS)[number]['value'];

export const DEFAULT_MARKDOWN_THEME: MarkdownThemePreset = 'docs';

const MARKDOWN_THEME_CLASSNAME: Record<MarkdownThemePreset, string> = {
  docs: 'markdown-theme-docs',
  github: 'markdown-theme-github',
  dense: 'markdown-theme-dense',
};

export function getMarkdownThemeClassName(theme: MarkdownThemePreset): string {
  return MARKDOWN_THEME_CLASSNAME[theme] ?? MARKDOWN_THEME_CLASSNAME[DEFAULT_MARKDOWN_THEME];
}
