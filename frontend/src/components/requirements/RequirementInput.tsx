'use client';

import { Plus } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import type { RequirementType } from '@/types/project';

interface RequirementInputProps {
  type: RequirementType;
  onAdd: (text: string) => void;
}

export function RequirementInput({ onAdd }: RequirementInputProps) {
  const [text, setText] = useState('');

  function handleAdd() {
    if (!text.trim()) return;
    onAdd(text.trim());
    setText('');
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleAdd();
    }
  }

  return (
    <div className='border-line-primary rounded-lg border p-4'>
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder='요구사항을 자유롭게 입력하세요. Ctrl+Enter로 추가합니다.'
        className='mb-3 min-h-20 resize-none border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0'
      />
      <div className='flex items-center justify-end'>
        <Button size='sm' onClick={handleAdd} disabled={!text.trim()}>
          <Plus className='size-3.5' />
          추가
        </Button>
      </div>
    </div>
  );
}
