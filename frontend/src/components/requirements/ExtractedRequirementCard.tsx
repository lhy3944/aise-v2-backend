'use client';

import { Check, X, Pencil } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import type { ExtractedRequirement, RequirementType } from '@/types/project';

const TYPE_LABELS: Record<RequirementType, string> = {
  fr: 'FR',
  qa: 'QA',
  constraints: 'Constraints',
  other: 'Other',
};

const TYPE_COLORS: Record<RequirementType, string> = {
  fr: 'bg-blue-500/10 text-blue-700 border-blue-500/30',
  qa: 'bg-green-500/10 text-green-700 border-green-500/30',
  constraints: 'bg-purple-500/10 text-purple-700 border-purple-500/30',
  other: 'bg-gray-500/10 text-gray-700 border-gray-500/30',
};

interface ExtractedRequirementCardProps {
  requirement: ExtractedRequirement;
  onAccept: (text: string, type: RequirementType) => void;
  onReject: () => void;
}

export function ExtractedRequirementCard({
  requirement,
  onAccept,
  onReject,
}: ExtractedRequirementCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(requirement.text);

  const isOther = requirement.type === 'other';

  function handleAccept() {
    // other 타입은 fr로 fallback
    const type: RequirementType = requirement.type === 'other' ? 'fr' : requirement.type;
    onAccept(editText, type);
  }

  return (
    <div className='border-line-subtle bg-canvas-primary rounded-lg border p-4'>
      <div className='mb-2 flex items-center justify-between'>
        <div className='flex items-center gap-2'>
          <Badge variant='outline' className={TYPE_COLORS[requirement.type]}>
            {TYPE_LABELS[requirement.type]}
          </Badge>
          {isOther && <span className='text-fg-muted text-xs'>(수락 시 FR로 분류)</span>}
        </div>
        <div className='flex shrink-0 gap-1'>
          {!isEditing && (
            <Button size='icon-xs' variant='ghost' onClick={() => setIsEditing(true)} title='수정'>
              <Pencil className='text-fg-muted size-3.5' />
            </Button>
          )}
          <Button size='icon-xs' variant='ghost' onClick={onReject} title='거절'>
            <X className='text-fg-muted size-3.5' />
          </Button>
          <Button size='icon-xs' onClick={handleAccept} title='수락'>
            <Check className='size-3.5' />
          </Button>
        </div>
      </div>

      {isEditing ? (
        <div className='space-y-2'>
          <Textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            className='min-h-12 text-sm'
          />
          <div className='flex justify-end gap-1'>
            <Button
              size='sm'
              variant='ghost'
              onClick={() => {
                setEditText(requirement.text);
                setIsEditing(false);
              }}
            >
              취소
            </Button>
            <Button size='sm' onClick={() => setIsEditing(false)}>
              확인
            </Button>
          </div>
        </div>
      ) : (
        <p className='text-fg-primary text-sm'>{editText}</p>
      )}

      <p className='text-fg-muted mt-2 text-xs'>{requirement.reason}</p>
    </div>
  );
}
