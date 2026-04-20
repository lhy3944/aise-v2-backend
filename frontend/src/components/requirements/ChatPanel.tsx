'use client';

import { Send, Bot, User } from 'lucide-react';
import { useCallback, useRef, useState, useEffect } from 'react';
import { ExtractedRequirementList } from '@/components/requirements/ExtractedRequirementList';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';
import { ApiError } from '@/lib/api';
import { showToast } from '@/lib/toast';
import { assistService } from '@/services/assist-service';
import { requirementService } from '@/services/requirement-service';
import { useOverlayStore } from '@/stores/overlay-store';
import type {
  ChatMessage,
  ExtractedRequirement,
  Requirement,
  RequirementType,
} from '@/types/project';

interface ChatPanelProps {
  projectId: string;
  onRequirementAdded: (requirement: Requirement) => void;
}

interface DisplayMessage {
  role: 'user' | 'assistant';
  content: string;
  extractedRequirements?: ExtractedRequirement[];
}

export function ChatPanel({ projectId, onRequirementAdded }: ChatPanelProps) {
  const { showConfirm } = useOverlayStore();

  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const MAX_HISTORY_TURNS = 20;
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  async function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    const userMessage: DisplayMessage = { role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsSending(true);

    try {
      const response = await assistService.chat(projectId, {
        message: trimmed,
        history,
      });

      const assistantMessage: DisplayMessage = {
        role: 'assistant',
        content: response.reply,
        extractedRequirements:
          response.extracted_requirements.length > 0 ? response.extracted_requirements : undefined,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setHistory((prev) => {
        const updated = [
          ...prev,
          { role: 'user' as const, content: trimmed },
          { role: 'assistant' as const, content: response.reply },
        ];
        return updated.slice(-MAX_HISTORY_TURNS * 2);
      });
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'AI 대화 중 오류가 발생했습니다.';
      showToast.error(msg);
      setMessages((prev) => prev.slice(0, -1));
      setInput(trimmed);
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // 체크박스에서 선택한 요구사항 반영 (확인 다이얼로그 포함)
  function handleConfirmExtracted(
    messageIndex: number,
    selected: { text: string; type: RequirementType }[],
  ) {
    if (selected.length === 0) return;

    showConfirm({
      title: '요구사항 반영',
      description: `선택한 ${selected.length}건의 요구사항을 추가하시겠습니까?`,
      onConfirm: async () => {
        let addedCount = 0;
        const failedItems: { text: string; type: RequirementType }[] = [];
        for (const item of selected) {
          try {
            const created = await requirementService.create(projectId, {
              type: item.type,
              original_text: item.text,
            });
            onRequirementAdded(created);
            addedCount++;
          } catch {
            failedItems.push(item);
          }
        }

        if (failedItems.length > 0) {
          // 실패한 항목만 남기기
          const failedTexts = new Set(failedItems.map((f) => f.text));
          setMessages((prev) =>
            prev.map((msg, i) => {
              if (i !== messageIndex || !msg.extractedRequirements) return msg;
              const remaining = msg.extractedRequirements.filter((r) => failedTexts.has(r.text));
              return {
                ...msg,
                extractedRequirements: remaining.length > 0 ? remaining : undefined,
              };
            }),
          );
          showToast.warning(
            `${addedCount}건 추가, ${failedItems.length}건 실패. 실패한 항목은 다시 시도할 수 있습니다.`,
          );
        } else {
          // 전부 성공 — 리스트 제거
          setMessages((prev) =>
            prev.map((msg, i) => {
              if (i !== messageIndex) return msg;
              return { ...msg, extractedRequirements: undefined };
            }),
          );
          showToast.success(`${addedCount}건의 요구사항이 추가되었습니다.`);
        }
      },
    });
  }

  function handleDismissExtracted(messageIndex: number) {
    setMessages((prev) =>
      prev.map((msg, i) => {
        if (i !== messageIndex) return msg;
        return { ...msg, extractedRequirements: undefined };
      }),
    );
  }

  return (
    <div className='border-line-subtle bg-canvas-primary flex h-[600px] flex-col rounded-lg border'>
      {/* Messages */}
      <div ref={scrollRef} className='flex-1 overflow-y-auto p-4'>
        {messages.length === 0 ? (
          <div className='flex h-full items-center justify-center'>
            <div className='text-center'>
              <Bot className='text-fg-muted/40 mx-auto mb-3 size-10' />
              <p className='text-fg-muted text-sm'>대화를 통해 요구사항을 정의해보세요.</p>
              <p className='text-fg-muted/60 mt-1 text-xs'>
                자연어로 시스템의 요구사항을 설명하면 AI가 대화를 이어갑니다.
              </p>
              <p className='text-fg-muted/60 mt-0.5 text-xs'>
                &ldquo;정리해줘&rdquo;라고 말하면 대화 내용에서 요구사항을 추출합니다.
              </p>
            </div>
          </div>
        ) : (
          <div className='flex flex-col gap-4'>
            {messages.map((msg, msgIdx) => (
              <div key={msgIdx}>
                {/* Message bubble */}
                <div
                  className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  <div
                    className={`flex size-7 shrink-0 items-center justify-center rounded-full ${
                      msg.role === 'user' ? 'bg-primary/10 text-primary' : 'bg-muted text-fg-muted'
                    }`}
                  >
                    {msg.role === 'user' ? <User className='size-4' /> : <Bot className='size-4' />}
                  </div>
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2.5 text-sm ${
                      msg.role === 'user'
                        ? 'bg-primary/10 text-fg-primary'
                        : 'bg-muted text-fg-primary'
                    }`}
                  >
                    <p className='whitespace-pre-wrap'>{msg.content}</p>
                  </div>
                </div>

                {/* Extracted requirements — 체크박스 리스트 */}
                {msg.extractedRequirements && msg.extractedRequirements.length > 0 && (
                  <div className='mt-3 ml-10'>
                    <ExtractedRequirementList
                      requirements={msg.extractedRequirements}
                      onConfirm={(selected) => handleConfirmExtracted(msgIdx, selected)}
                      onDismiss={() => handleDismissExtracted(msgIdx)}
                    />
                  </div>
                )}
              </div>
            ))}

            {/* Loading indicator */}
            {isSending && (
              <div className='flex gap-3'>
                <div className='bg-muted text-fg-muted flex size-7 shrink-0 items-center justify-center rounded-full'>
                  <Bot className='size-4' />
                </div>
                <div className='bg-muted flex items-center gap-2 rounded-lg px-4 py-2.5'>
                  <Spinner className='size-4' />
                  <span className='text-fg-muted text-sm'>AI가 응답 중입니다...</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className='border-line-subtle border-t p-4'>
        <div className='flex items-end gap-2'>
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='요구사항에 대해 설명해주세요... (Shift+Enter로 줄바꿈)'
            className='max-h-32 min-h-10 resize-none text-sm'
            disabled={isSending}
          />
          <Button
            size='sm'
            onClick={handleSend}
            disabled={!input.trim() || isSending}
            className='shrink-0'
          >
            <Send className='size-4' />
          </Button>
        </div>
      </div>
    </div>
  );
}
