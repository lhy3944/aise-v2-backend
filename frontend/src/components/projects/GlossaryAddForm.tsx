'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus } from 'lucide-react';
import type { GlossaryCreate } from '@/types/project';

interface GlossaryAddFormProps {
  onAdd: (data: GlossaryCreate) => void;
}

export function GlossaryAddForm({ onAdd }: GlossaryAddFormProps) {
  const [term, setTerm] = useState('');
  const [definition, setDefinition] = useState('');
  const [productGroup, setProductGroup] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!term.trim() || !definition.trim()) return;
    onAdd({
      term: term.trim(),
      definition: definition.trim(),
      product_group: productGroup.trim() || null,
    });
    setTerm('');
    setDefinition('');
    setProductGroup('');
  }

  return (
    <form onSubmit={handleSubmit} className='flex items-end gap-3'>
      <div className='flex flex-1 flex-col gap-1'>
        <Label htmlFor='glossary-term' variant='field'>
          용어
        </Label>
        <Input
          id='glossary-term'
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder='용어 입력'
          className='h-8 text-sm'
        />
      </div>
      <div className='flex flex-1 flex-col gap-1'>
        <Label htmlFor='glossary-def' variant='field'>
          정의
        </Label>
        <Input
          id='glossary-def'
          value={definition}
          onChange={(e) => setDefinition(e.target.value)}
          placeholder='정의 입력'
          className='h-8 text-sm'
        />
      </div>
      <div className='flex flex-1 flex-col gap-1'>
        <Label htmlFor='glossary-group' variant='field'>
          제품군
        </Label>
        <Input
          id='glossary-group'
          value={productGroup}
          onChange={(e) => setProductGroup(e.target.value)}
          placeholder='(선택)'
          className='h-8 text-sm'
        />
      </div>
      <Button size='sm' type='submit' disabled={!term.trim() || !definition.trim()}>
        <Plus className='size-3.5' />
        추가
      </Button>
    </form>
  );
}
