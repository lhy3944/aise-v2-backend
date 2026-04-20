'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { knowledgeService } from '@/services/knowledge-service';
import type {
  KnowledgeDocument,
  KnowledgeDocumentFileType,
} from '@/types/project';
import { Spinner } from '@/components/ui/spinner';
import { FileText } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import '@/components/ui/ai-elements/css/markdown.css';

interface KnowledgePreviewModalProps {
  document: KnowledgeDocument | null;
  projectId: string;
  onClose: () => void;
}

const FILE_TYPE_LABEL: Record<KnowledgeDocumentFileType, string> = {
  pdf: 'PDF',
  md: 'Markdown',
  txt: 'Text',
};

export function KnowledgePreviewModal({
  document: doc,
  projectId,
  onClose,
}: KnowledgePreviewModalProps) {
  const [previewText, setPreviewText] = useState('');
  const [totalChars, setTotalChars] = useState(0);
  const [loading, setLoading] = useState(false);

  const canRender = doc?.file_type === 'md';
  const defaultTab = canRender ? 'rendered' : 'raw';

  const fetchPreview = useCallback(async () => {
    if (!doc) return;
    setLoading(true);
    try {
      const preview = await knowledgeService.preview(
        projectId,
        doc.document_id,
      );
      setPreviewText(preview.preview_text);
      setTotalChars(preview.total_characters);
    } catch {
      setPreviewText('미리보기를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, [doc, projectId]);

  useEffect(() => {
    if (doc) {
      fetchPreview();
    }
  }, [doc, fetchPreview]);

  return (
    <Dialog open={!!doc} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className='flex flex-col gap-0 p-0 sm:max-w-4xl'>
        <DialogHeader className='border-line-primary border-b px-6 py-4 pr-12'>
          <div className='flex items-center gap-3'>
            <div className='bg-canvas-surface flex size-8 shrink-0 items-center justify-center rounded-md'>
              <FileText className='text-fg-muted size-4' />
            </div>
            <div className='min-w-0 flex-1'>
              <DialogTitle className='truncate text-sm'>
                {doc?.name}
              </DialogTitle>
              <p className='text-fg-muted text-xs'>
                {
                  FILE_TYPE_LABEL[
                    (doc?.file_type as KnowledgeDocumentFileType) ?? 'txt'
                  ]
                }
                {totalChars > 0 && ` · ${totalChars.toLocaleString()}자`}
                {previewText.length > 0 &&
                  previewText.length < totalChars &&
                  ' (일부만 표시)'}
              </p>
            </div>
          </div>
        </DialogHeader>

        <div className='flex min-h-0 flex-1 flex-col'>
          {loading ? (
            <div className='flex items-center justify-center py-12'>
              <Spinner size='size-6' className='text-fg-muted' />
            </div>
          ) : canRender ? (
            <Tabs
              defaultValue={defaultTab}
              className='flex min-h-0 flex-1 flex-col'
            >
              <TabsList
                variant='line'
                className='border-line-subtle w-full shrink-0 justify-start border-b px-6'
              >
                <TabsTrigger
                  value='rendered'
                  className='data-[state=active]:text-accent-primary after:bg-accent-primary'
                >
                  렌더링
                </TabsTrigger>
                <TabsTrigger
                  value='raw'
                  className='data-[state=active]:text-accent-primary after:bg-accent-primary'
                >
                  원문
                </TabsTrigger>
              </TabsList>
              <TabsContent
                value='rendered'
                className='min-h-0 flex-1 overflow-y-auto px-6 py-4'
              >
                <div className='source-markdown text-fg-primary text-sm'>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {previewText}
                  </ReactMarkdown>
                </div>
              </TabsContent>
              <TabsContent
                value='raw'
                className='min-h-0 flex-1 overflow-y-auto px-6 py-4'
              >
                <pre className='text-fg-secondary whitespace-pre-wrap text-xs leading-relaxed'>
                  {previewText}
                </pre>
              </TabsContent>
            </Tabs>
          ) : (
            <div className='min-h-0 flex-1 overflow-y-auto px-6 py-4'>
              <pre className='text-fg-secondary whitespace-pre-wrap text-xs leading-relaxed'>
                {previewText}
              </pre>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
