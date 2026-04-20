'use client';

import { useEffect } from 'react';

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (target.isContentEditable) return true;
  return false;
}

/**
 * `/` 키로 프롬프트 입력창 포커스, `Esc` 키로 포커스 해제.
 * 다른 입력 필드/오버레이(dialog)가 활성일 때는 동작하지 않음.
 */
export function useFocusPromptInput() {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.isComposing) return;

      if (
        e.key === '/' &&
        !e.metaKey &&
        !e.ctrlKey &&
        !e.altKey &&
        !e.shiftKey
      ) {
        if (isEditableTarget(e.target)) return;
        if (document.querySelector('[role="dialog"][data-state="open"]'))
          return;

        const textarea = document.querySelector<HTMLTextAreaElement>(
          'textarea[name="message"]',
        );
        if (!textarea || textarea.disabled) return;

        e.preventDefault();
        textarea.focus();
        const len = textarea.value.length;
        textarea.setSelectionRange(len, len);
        return;
      }

      if (
        e.key === 'Escape' &&
        e.target instanceof HTMLTextAreaElement &&
        e.target.name === 'message'
      ) {
        e.target.blur();
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);
}
