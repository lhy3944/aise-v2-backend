'use client';

import { ChatInput } from '@/components/chat/ChatInput';
import { MessageRenderer } from '@/components/chat/MessageRenderer';
import { PromptSuggestions } from '@/components/chat/PromptSuggestions';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useChatScroll } from '@/hooks/useChatScroll';
import { useChatStream } from '@/hooks/useChatStream';
import { useTurnLayout } from '@/hooks/useTurnLayout';
import { cn } from '@/lib/utils';
import { usePanelStore } from '@/stores/panel-store';
import { useProjectStore } from '@/stores/project-store';
import { Spinner } from '@/components/ui/spinner';
import { ArrowDown, ShieldAlert } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useMemo, useRef } from 'react';

interface ChatAreaProps {
  sessionId?: string;
}

export function ChatArea({ sessionId }: ChatAreaProps) {
  const fullWidthMode = usePanelStore((s) => s.fullWidthMode);
  const currentProject = useProjectStore((s) => s.currentProject);

  const {
    messages,
    isStreaming,
    isLoadingMessages,
    isCreatingSession,
    sendMessage,
    stopStreaming,
    setInputValue,
    resumeFromInterrupt,
  } = useChatStream(sessionId);

  const { scrollRef, setScrollEl, isAtBottom, scrollToBottom } =
    useChatScroll(messages);
  const { pastMessages, currentTurn, currentTurnRef, answerAreaRef } =
    useTurnLayout(messages, scrollRef);

  const chatContainerRef = useRef<HTMLDivElement>(null);

  const hasMessages = messages.length > 0;
  const showChat = hasMessages || isStreaming || isLoadingMessages;
  const maxW = fullWidthMode ? 'max-w-[896px]' : 'max-w-[768px]';

  const pendingHitlInterruptId = useMemo(() => {
    for (const msg of messages) {
      if (msg.hitlData && msg.hitlResponded !== true) {
        return msg.hitlData.interrupt_id;
      }
    }
    return null;
  }, [messages]);

  const handleHitlRespond = (
    response: Record<string, unknown>,
    threadId: string,
    _sessionId: string,
  ) => {
    resumeFromInterrupt(response, threadId, sessionId);
  };

  const scrollToHitlCard = () => {
    if (!pendingHitlInterruptId || !chatContainerRef.current) return;
    const el = chatContainerRef.current.querySelector(
      `[data-hitl-interrupt-id="${pendingHitlInterruptId}"]`,
    );
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const isFirstSessionResponse =
    messages.length === 2 &&
    messages[0].role === 'user' &&
    messages[1].role === 'assistant' &&
    !messages[1].content;

  return (
    <div className='flex flex-1 flex-col overflow-hidden'>
      <div className='relative flex-1 overflow-hidden'>
        {showChat ? (
          /* 대화 모드 */
          <div className='relative h-full' ref={chatContainerRef}>
            {isLoadingMessages && !hasMessages ? (
              <div className='flex h-full items-center justify-center'>
                <Spinner size='size-8' className='text-fg-muted' />
              </div>
            ) : (
              <ScrollArea className='h-full' viewportRef={setScrollEl}>
                <div
                  className={cn(
                    'mx-auto px-4 sm:px-6 pt-6 transition-[max-width] duration-300',
                    maxW,
                  )}
                >
                  {pastMessages.length > 0 && (
                    <MessageRenderer
                      messages={pastMessages}
                      onHitlRespond={handleHitlRespond}
                      isSessionStreaming={isStreaming}
                    />
                  )}

                  {currentTurn && (
                    <section
                      ref={currentTurnRef}
                      className={cn(
                        'flex flex-col gap-6',
                        pastMessages.length > 0 && 'mt-6',
                      )}
                    >
                      <div className='shrink-0'>
                        <MessageRenderer messages={[currentTurn.question]} />
                      </div>
                      <div ref={answerAreaRef}>
                        <MessageRenderer
                          messages={[currentTurn.answer]}
                          onSendMessage={sendMessage}
                          onHitlRespond={handleHitlRespond}
                          firstResponseSkeleton={isFirstSessionResponse}
                          isSessionStreaming={isStreaming}
                        />
                      </div>
                    </section>
                  )}
                </div>
              </ScrollArea>
            )}

            {/* Scroll to bottom */}
            <AnimatePresence>
              {!isAtBottom && hasMessages && (
                <motion.button
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.15 }}
                  onClick={scrollToBottom}
                  className='bg-canvas-surface border-line-primary text-fg-secondary hover:text-fg-primary absolute bottom-3 left-1/2 -translate-x-1/2 cursor-pointer rounded-full border p-2 shadow-md transition-colors'
                  aria-label='하단으로 스크롤'
                >
                  <ArrowDown className='size-4' />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        ) : (
          /* 빈 화면: 중앙 프롬프트 */
          <div className='flex h-full flex-col justify-start px-4 pt-8 sm:pt-[12vh]'>
            <div
              className={cn(
                'mx-auto w-full transition-[max-width] duration-300',
                maxW,
              )}
            >
              <div className='flex justify-center py-4'>
                <h1 className='text-fg-primary flex items-center justify-center text-4xl font-bold'>
                  {['A', 'I', 'S', 'E', ' ', '3', '.', '0'].map((char, i) => (
                    <motion.span
                      key={i}
                      className='inline-block'
                      animate={{ y: [0, -6, 0] }}
                      transition={{
                        duration: 0.4,
                        repeat: Infinity,
                        repeatDelay: 5,
                        delay: i * 0.1,
                      }}
                    >
                      {char}
                    </motion.span>
                  ))}
                </h1>
              </div>

              {!currentProject && (
                <div className='text-fg-muted mb-4 text-center text-sm'>
                  프로젝트를 선택하면 에이전트와 대화를 시작할 수 있습니다.
                </div>
              )}

              <div className='mt-4'>
                <ChatInput
                  onSubmit={sendMessage}
                  onAction={sendMessage}
                  onStop={stopStreaming}
                  isStreaming={isStreaming}
                  isSubmitting={isCreatingSession}
                  disabled={!currentProject || isCreatingSession}
                />
              </div>
              <div className='flex flex-col items-center justify-center text-xs/5 tracking-normal'>
                <div className='text-muted-foreground'>
                  AISE can make mistakes. Check important info.
                </div>
              </div>
              <PromptSuggestions rows={1} onSelect={setInputValue} />
            </div>
          </div>
        )}
      </div>

      {/* 하단 고정 입력 */}
      {showChat && (
        <div className='shrink-0 px-4 pt-2 pb-4'>
          <div
            className={cn('mx-auto transition-[max-width] duration-300', maxW)}
          >
            <AnimatePresence>
              {pendingHitlInterruptId && (
                <motion.button
                  key='hitl-banner'
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{
                    opacity: 0,
                    height: 0,
                    transition: { duration: 0.15 },
                  }}
                  transition={{ duration: 0.2 }}
                  onClick={scrollToHitlCard}
                  className='border-line-primary bg-canvas-surface text-fg-secondary hover:text-fg-primary hover:bg-canvas-secondary mb-2 flex w-full cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors overflow-hidden'
                >
                  <ShieldAlert className='size-4 shrink-0 text-warning' />
                  <span className='flex-1 text-left'>승인 대기 중</span>
                  <ArrowDown className='size-4 shrink-0 rotate-180' />
                </motion.button>
              )}
            </AnimatePresence>
            <ChatInput
              onSubmit={sendMessage}
              onAction={sendMessage}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              disabled={!currentProject}
              autoFocus={false}
            />
          </div>
        </div>
      )}
    </div>
  );
}
