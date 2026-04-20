'use client';

import { Pencil, Trash2, X, Check } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { Requirement } from '@/types/project';

interface RequirementItemProps {
  requirement: Requirement;
  onToggleSelect: (id: string, selected: boolean) => void;
  onUpdate: (id: string, originalText: string) => void;
  onDelete: (id: string) => void;
}

export function RequirementItem({
  requirement,
  onToggleSelect,
  onUpdate,
  onDelete,
}: RequirementItemProps) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(requirement.original_text);

  function handleSave() {
    if (!editText.trim()) return;
    onUpdate(requirement.requirement_id, editText.trim());
    setEditing(false);
  }

  function handleCancel() {
    setEditText(requirement.original_text);
    setEditing(false);
  }

  return (
    <div
      className={cn(
        'group border-line-subtle flex gap-3 rounded-md border px-4 py-3 transition-colors',
        requirement.is_selected && 'border-accent-primary/30 bg-accent-primary/5',
      )}
    >
      <Checkbox
        checked={requirement.is_selected}
        onCheckedChange={(checked) => onToggleSelect(requirement.requirement_id, checked)}
        className='mt-0.5'
      />

      <div className='min-w-0 flex-1'>
        {editing ? (
          <div className='flex flex-col gap-2'>
            <Textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className='min-h-16 resize-none text-sm'
              autoFocus
            />
            <div className='flex gap-1.5'>
              <Button size='xs' onClick={handleSave} disabled={!editText.trim()}>
                <Check className='size-3' />
                저장
              </Button>
              <Button size='xs' variant='ghost' onClick={handleCancel}>
                <X className='size-3' />
                취소
              </Button>
            </div>
          </div>
        ) : (
          <div className='flex flex-col gap-1.5'>
            <p className='text-fg-primary text-sm'>{requirement.original_text}</p>
            {requirement.refined_text && (
              <div className='bg-accent-primary/5 border-accent-primary/20 rounded-md border px-3 py-2'>
                <span className='text-accent-primary text-xs font-medium'>AI 정제</span>
                <p className='text-fg-secondary mt-0.5 text-sm'>{requirement.refined_text}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {!editing && (
        <div className='flex shrink-0 items-start gap-1 opacity-0 transition-opacity group-hover:opacity-100'>
          <Button size='icon-xs' variant='ghost' onClick={() => setEditing(true)} title='수정'>
            <Pencil className='size-3' />
          </Button>
          <Button
            size='icon-xs'
            variant='ghost'
            onClick={() => onDelete(requirement.requirement_id)}
            title='삭제'
            className='text-destructive hover:text-destructive'
          >
            <Trash2 className='size-3' />
          </Button>
        </div>
      )}
    </div>
  );
}
