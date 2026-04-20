'use client';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Spinner } from '@/components/ui/spinner';
import type { GlossaryCreate } from '@/types/project';
import { Plus } from 'lucide-react';
import { useState } from 'react';

interface GlossaryGenerateListProps {
  generated: GlossaryCreate[];
  selected: Set<number>;
  onToggle: (idx: number) => void;
  onToggleAll: () => void;
}

export function GlossaryGenerateList({
  generated,
  selected,
  onToggle,
  onToggleAll,
}: GlossaryGenerateListProps) {
  const allSelected = generated.length > 0 && selected.size === generated.length;
  const someSelected = selected.size > 0 && !allSelected;

  return (
    <div className='flex flex-col gap-2'>
      {/* 전체 선택 */}
      <label className='flex cursor-pointer items-center gap-2 pb-1'>
        <Checkbox
          checked={allSelected}
          indeterminate={someSelected}
          onCheckedChange={onToggleAll}
        />
        <span className='text-fg-secondary text-sm'>
          전체 선택 ({selected.size}/{generated.length})
        </span>
      </label>

      {/* 용어 리스트 */}
      <div className='flex flex-col gap-1.5'>
        {generated.map((item, idx) => (
          <label
            key={idx}
            className='border-line-subtle bg-canvas-primary hover:bg-canvas-surface/50 flex cursor-pointer items-start gap-2.5 rounded-md border px-3 py-2 transition-colors'
          >
            <Checkbox
              checked={selected.has(idx)}
              onCheckedChange={() => onToggle(idx)}
              className='mt-0.5'
            />
            <div className='min-w-0 flex-1'>
              <span className='text-fg-primary text-sm font-medium'>{item.term}</span>
              <p className='text-fg-secondary text-xs'>{item.definition}</p>
              {item.product_group && (
                <span className='text-fg-muted text-xs'>{item.product_group}</span>
              )}
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}

/** Modal footer 액션 버튼 */
export function GlossaryGenerateActions({
  selectedCount,
  onApply,
  onCancel,
  isLoading = false,
}: {
  selectedCount: number;
  onApply: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}) {
  return (
    <div className='flex justify-end gap-2'>
      <Button variant='outline' onClick={onCancel} disabled={isLoading}>
        취소
      </Button>
      <Button onClick={onApply} disabled={selectedCount === 0 || isLoading}>
        {isLoading ? <Spinner className='size-3.5' /> : <Plus className='size-3.5' />}
        {isLoading ? '추가 중...' : `선택 항목 추가 (${selectedCount})`}
      </Button>
    </div>
  );
}

/** 선택 상태를 관리하는 커스텀 훅 */
export function useGlossarySelection(count: number) {
  const [selected, setSelected] = useState<Set<number>>(
    new Set(Array.from({ length: count }, (_, i) => i)),
  );

  function toggle(idx: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === count) {
      setSelected(new Set());
    } else {
      setSelected(new Set(Array.from({ length: count }, (_, i) => i)));
    }
  }

  function reset(newCount: number) {
    setSelected(new Set(Array.from({ length: newCount }, (_, i) => i)));
  }

  return { selected, toggle, toggleAll, reset };
}
