'use client';

import { CheckSquare } from 'lucide-react';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import type { ExtractedRequirement, RequirementType } from '@/types/project';

const TYPE_LABELS: Record<string, string> = {
  fr: 'Functional Requirements',
  qa: 'Quality Attributes',
  constraints: 'Constraints',
  other: 'Other',
};

const TYPE_BADGE_COLORS: Record<string, string> = {
  fr: 'bg-blue-500/10 text-blue-700 border-blue-500/30',
  qa: 'bg-green-500/10 text-green-700 border-green-500/30',
  constraints: 'bg-purple-500/10 text-purple-700 border-purple-500/30',
  other: 'bg-gray-500/10 text-gray-700 border-gray-500/30',
};

interface ExtractedRequirementListProps {
  requirements: ExtractedRequirement[];
  onConfirm: (selected: { text: string; type: RequirementType }[]) => void;
  onDismiss: () => void;
}

export function ExtractedRequirementList({
  requirements,
  onConfirm,
  onDismiss,
}: ExtractedRequirementListProps) {
  const [checkedIndices, setCheckedIndices] = useState<Set<number>>(() => new Set());

  function toggleCheck(index: number) {
    setCheckedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }

  function handleConfirm() {
    const selected = requirements
      .filter((_, i) => checkedIndices.has(i))
      .map((req) => ({
        text: req.text,
        type: (req.type === 'other' ? 'fr' : req.type) as RequirementType,
      }));
    onConfirm(selected);
  }

  // 타입별 그룹화 (FR → QA → Constraints 고정 순서)
  const TYPE_ORDER = ['fr', 'qa', 'constraints', 'other'] as const;
  const groupMap = new Map<string, { req: ExtractedRequirement; index: number }[]>();
  requirements.forEach((req, index) => {
    const key = req.type;
    if (!groupMap.has(key)) groupMap.set(key, []);
    groupMap.get(key)!.push({ req, index });
  });
  const grouped = TYPE_ORDER.filter((t) => groupMap.has(t)).map(
    (t) => [t, groupMap.get(t)!] as const,
  );

  const checkedCount = checkedIndices.size;

  return (
    <div className='border-accent-primary/30 bg-accent-primary/5 rounded-lg border p-4'>
      <div className='mb-3 flex items-center justify-between'>
        <div className='flex items-center gap-2'>
          <CheckSquare className='text-accent-primary size-4' />
          <span className='text-fg-primary text-sm font-medium'>
            추출된 요구사항 ({requirements.length}건)
          </span>
        </div>
        <span className='text-fg-muted text-xs'>{checkedCount}건 선택됨</span>
      </div>

      {/* 타입별 그룹 */}
      <div className='space-y-4'>
        {grouped.map(([type, items]) => (
          <div key={type}>
            <div className='mb-2 flex items-center gap-2'>
              <Badge
                variant='outline'
                className={TYPE_BADGE_COLORS[type] || TYPE_BADGE_COLORS.other}
              >
                {TYPE_LABELS[type] || type}
              </Badge>
              <span className='text-fg-muted text-xs'>({items.length})</span>
            </div>
            <div className='ml-1 space-y-1.5'>
              {items.map(({ req, index }) => (
                <label
                  key={index}
                  className='hover:bg-muted/50 flex cursor-pointer items-start gap-2.5 rounded-md px-2 py-1.5 transition-colors'
                >
                  <Checkbox
                    checked={checkedIndices.has(index)}
                    onCheckedChange={() => toggleCheck(index)}
                    className='mt-0.5'
                  />
                  <div className='min-w-0 flex-1'>
                    <p className='text-fg-primary text-sm'>{req.text}</p>
                    <p className='text-fg-muted mt-0.5 text-xs'>{req.reason}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className='border-line-subtle mt-4 flex items-center justify-end gap-2 border-t pt-3'>
        <Button size='sm' variant='ghost' onClick={onDismiss}>
          닫기
        </Button>
        <Button size='sm' onClick={handleConfirm} disabled={checkedCount === 0}>
          <CheckSquare className='size-3.5' />
          {checkedCount}건 반영
        </Button>
      </div>
    </div>
  );
}
