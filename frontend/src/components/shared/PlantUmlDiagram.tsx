'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTheme } from 'next-themes';

import { getMarkdownThemeClassName } from '@/config/markdown-theme';
import { cn } from '@/lib/utils';
import { extractPlantUmlBlocks, plantumlImageUrl } from '@/lib/plantuml';
import { useUiPreferenceStore } from '@/stores/ui-preference-store';

import '@/components/ui/ai-elements/css/markdown.css';

interface PlantUmlDiagramProps {
  content: string;
  className?: string;
}

/** 섹션 content에서 PlantUML 블록을 추출해 이미지로 렌더링.
 *  PlantUML 블록이 없으면 일반 텍스트를 표시.
 *  다크/라이트 테마에 따라 PlantUML skinparam을 자동 주입.
 *  PlantUML 외 마크다운 텍스트는 ReactMarkdown으로 렌더링.
 */
export function PlantUmlDiagram({ content, className }: PlantUmlDiagramProps) {
  const blocks = extractPlantUmlBlocks(content);
  const nonPlantUmlContent = content
    .replace(/```plantuml\s*\n[\s\S]*?```/gi, '')
    .trim();

  if (blocks.length === 0) {
    return <MarkdownContent content={content} className={className} />;
  }

  return (
    <div className={cn('space-y-4', className)}>
      {blocks.map((code, idx) => (
        <PlantUmlImage key={idx} code={code} />
      ))}
      {nonPlantUmlContent && (
        <MarkdownContent content={nonPlantUmlContent} />
      )}
    </div>
  );
}

function MarkdownContent({ content, className }: { content: string; className?: string }) {
  const markdownTheme = useUiPreferenceStore((s) => s.markdownTheme);
  const markdownThemeClass = getMarkdownThemeClassName(markdownTheme);

  return (
    <div className={cn('source-markdown text-fg-primary text-sm', markdownThemeClass, className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}

function PlantUmlImage({ code }: { code: string }) {
  const { resolvedTheme } = useTheme();
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const isDark = resolvedTheme === 'dark';

  useEffect(() => {
    setError(false);
    plantumlImageUrl(code, { dark: isDark })
      .then(setUrl)
      .catch(() => setError(true));
  }, [code, isDark]);

  if (error || !url) {
    return (
      <pre className='bg-canvas-secondary overflow-x-auto rounded-md p-3 text-xs'>
        <code>{code}</code>
      </pre>
    );
  }

  return (
    <div className='bg-canvas-secondary overflow-x-auto rounded-md p-3'>
      <img
        src={url}
        alt='PlantUML Diagram'
        className='mx-auto max-w-full'
        onError={() => setError(true)}
      />
    </div>
  );
}
