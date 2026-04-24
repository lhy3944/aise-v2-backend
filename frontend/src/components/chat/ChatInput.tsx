'use client';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { streamExtractArtifactRecords } from '@/services/artifact-record-service';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { useArtifactStore } from '@/stores/artifact-store';
import { LayoutMode, usePanelStore } from '@/stores/panel-store';
import { useProjectStore } from '@/stores/project-store';
import { useReadinessStore } from '@/stores/readiness-store';
import { BookOpen, Database, FileText, Loader2, MicIcon, PaperclipIcon, RefreshCw, Zap } from 'lucide-react';
import Image from 'next/image';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Attachment,
  AttachmentHoverCard,
  AttachmentHoverCardContent,
  AttachmentHoverCardTrigger,
  AttachmentInfo,
  AttachmentPreview,
  AttachmentRemove,
  Attachments,
  getMediaCategory,
} from '@/components/ui/ai-elements/attachments';
import {
  PromptInput,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputAttachments,
} from '@/components/ui/ai-elements/prompt-input';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chat-store';

function AttachmentsDisplay() {
  const attachments = usePromptInputAttachments();

  if (attachments.files.length === 0) {
    return null;
  }

  return (
    <Attachments variant='inline' className='w-full p-2'>
      {attachments.files.map((file) => {
        const isImage = getMediaCategory(file) === 'image';
        return (
          <AttachmentHoverCard key={file.id}>
            <AttachmentHoverCardTrigger asChild>
              <Attachment data={file} onRemove={() => attachments.remove(file.id)}>
                <div className='relative size-5 shrink-0'>
                  <div className='absolute inset-0 transition-opacity group-hover:opacity-0'>
                    <AttachmentPreview />
                  </div>
                </div>
                <AttachmentRemove className='absolute' />
                <AttachmentInfo />
              </Attachment>
            </AttachmentHoverCardTrigger>
            {isImage && file.type === 'file' && file.url && (
              <AttachmentHoverCardContent>
                <Image
                  src={file.url}
                  alt={file.filename ?? 'Preview'}
                  width={220}
                  height={220}
                  className='max-h-60 max-w-60 rounded object-contain'
                />
              </AttachmentHoverCardContent>
            )}
          </AttachmentHoverCard>
        );
      })}
    </Attachments>
  );
}

function AttachButton() {
  const attachments = usePromptInputAttachments();
  return (
    <PromptInputButton tooltip='파일 첨부' onClick={attachments.openFileDialog}>
      <PaperclipIcon size={16} />
    </PromptInputButton>
  );
}

function VoiceButton() {
  const setInputValue = useChatStore((s) => s.setInputValue);
  const inputValue = useChatStore((s) => s.inputValue);
  const [isListening, setIsListening] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const inputValueRef = useRef(inputValue);
  const interimLengthRef = useRef(0);

  useEffect(() => {
    inputValueRef.current = inputValue;
  }, [inputValue]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
    };
  }, []);

  const handleClick = useCallback(() => {
    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognitionAPI =
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).SpeechRecognition ??
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition: any = new SpeechRecognitionAPI();
    recognition.lang = 'ko-KR';
    recognition.interimResults = true;
    recognition.continuous = true;
    recognitionRef.current = recognition;

    recognition.onstart = () => setIsListening(true);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      let interim = '';
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }

      const base = inputValueRef.current.slice(
        0,
        inputValueRef.current.length - interimLengthRef.current,
      );
      setInputValue(base + (final || interim));
      interimLengthRef.current = final ? 0 : interim.length;
    };

    recognition.onend = () => {
      setIsListening(false);
      interimLengthRef.current = 0;
    };

    recognition.onerror = () => {
      setIsListening(false);
      interimLengthRef.current = 0;
    };

    recognition.start();
  }, [isListening, setInputValue]);

  return (
    <PromptInputButton
      tooltip={{ content: '마이크', shortcut: '⌘M', side: 'bottom' }}
      onClick={handleClick}
      className={cn(isListening && 'bg-canvas-surface text-accent-primary hover:bg-canvas-surface')}
    >
      <MicIcon size={16} className={cn(isListening && 'animate-pulse')} />
    </PromptInputButton>
  );
}

function ActionsButton({ onAction }: { onAction?: (text: string) => void }) {
  const currentProject = useProjectStore((s) => s.currentProject);
  const readiness = useReadinessStore((s) => s.data);
  const extracting = useArtifactRecordStore((s) => s.extracting);
  const setExtracting = useArtifactRecordStore((s) => s.setExtracting);
  const setCandidates = useArtifactRecordStore((s) => s.setCandidates);
  const setExtractError = useArtifactRecordStore((s) => s.setExtractError);
  const setActiveTab = useArtifactStore((s) => s.setActiveTab);
  const setRightPanelPreset = usePanelStore((s) => s.setRightPanelPreset);

  const isReady = readiness?.is_ready ?? false;

  const handleExtractRecords = useCallback(() => {
    if (!currentProject || extracting) return;
    setExtracting(true);
    onAction?.('레코드 추출을 시작합니다...');
    streamExtractArtifactRecords(currentProject.project_id, undefined, {
      onDone: (candidates) => {
        setCandidates(candidates);
        setActiveTab('records');
        setRightPanelPreset(LayoutMode.SPLIT);
      },
      onError: (msg) => {
        setExtractError(msg);
        onAction?.(`레코드 추출 실패: ${msg}`);
      },
    });
  }, [currentProject, extracting, onAction, setExtracting, setCandidates, setExtractError, setActiveTab, setRightPanelPreset]);

  const actions = [
    {
      id: 'extract',
      icon: extracting ? Loader2 : Database,
      label: extracting ? '추출 중...' : '레코드 추출',
      enabled: isReady && !extracting,
      spinning: extracting,
      onClick: handleExtractRecords,
    },
    {
      id: 'srs',
      icon: FileText,
      label: 'SRS 문서 생성',
      enabled: false,
      onClick: () => onAction?.('SRS 문서 생성을 시작해주세요.'),
    },
    {
      id: 'glossary-review',
      icon: BookOpen,
      label: '용어집 검토',
      enabled: false,
      onClick: () => onAction?.('미승인 용어를 검토해주세요.'),
    },
    {
      id: 'srs-regenerate',
      icon: RefreshCw,
      label: 'SRS 재생성',
      enabled: false,
      onClick: () => onAction?.('SRS 문서를 재생성해주세요.'),
    },
  ];

  if (!currentProject) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className='text-fg-muted hover:text-fg-primary hover:bg-canvas-surface flex size-8 items-center justify-center rounded-md transition-colors'>
          <Zap size={16} />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align='start' className='w-48'>
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <DropdownMenuItem
              key={action.id}
              onClick={action.onClick}
              disabled={!action.enabled}
              className='gap-2 text-xs'
            >
              <Icon className={cn('size-4 shrink-0', action.spinning && 'animate-spin')} />
              {action.label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function ChatInput({
  onSubmit,
  onAction,
  onStop,
  disabled,
  isStreaming,
  isSubmitting,
  autoFocus = true,
}: {
  onSubmit?: (text: string) => void;
  onAction?: (text: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  isSubmitting?: boolean;
  autoFocus?: boolean;
}) {
  const inputValue = useChatStore((s) => s.inputValue);
  const setInputValue = useChatStore((s) => s.setInputValue);

  const handleSubmit = () => {
    if (!inputValue.trim() || disabled) return;
    onSubmit?.(inputValue.trim());
  };

  return (
    <PromptInput globalDrop multiple maxFiles={5} onSubmit={handleSubmit}>
      <PromptInputBody>
        <AttachmentsDisplay />
        <PromptInputTextarea
          autoFocus={autoFocus}
          value={inputValue}
          onChange={(e) => setInputValue(e.currentTarget.value)}
          disabled={disabled}
        />
      </PromptInputBody>
      <PromptInputFooter>
        <PromptInputTools>
          <AttachButton />
          <VoiceButton />
          <ActionsButton onAction={onAction} />
        </PromptInputTools>
        <PromptInputSubmit
          disabled={!inputValue?.trim() && !isStreaming && !isSubmitting}
          status={isSubmitting ? 'submitted' : isStreaming ? 'streaming' : undefined}
          onStop={onStop}
        />
      </PromptInputFooter>
    </PromptInput>
  );
}
