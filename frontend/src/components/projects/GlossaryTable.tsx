'use client';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { GlossaryCreate, GlossaryItem } from '@/types/project';
import { BookOpen, Check, Pencil, Plus, Search, Sparkles, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';

/* ─── Inline Edit Row ─── */

interface EditRowProps {
  initial?: { term: string; definition: string; productGroup: string };
  onSave: (data: { term: string; definition: string; product_group: string | null }) => void;
  onCancel: () => void;
  autoFocus?: boolean;
}

function EditRow({ initial, onSave, onCancel, autoFocus }: EditRowProps) {
  const [term, setTerm] = useState(initial?.term ?? '');
  const [definition, setDefinition] = useState(initial?.definition ?? '');
  const [productGroup, setProductGroup] = useState(initial?.productGroup ?? '');

  function handleSave() {
    if (!term.trim() || !definition.trim()) return;
    onSave({
      term: term.trim(),
      definition: definition.trim(),
      product_group: productGroup.trim() || null,
    });
  }

  return (
    <TableRow className='border-accent-primary/30 bg-canvas-surface/30 hover:bg-canvas-surface/30'>
      <TableCell />
      <TableCell>
        <Input
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder='용어'
          className='text-sm'
          autoFocus={autoFocus}
        />
      </TableCell>
      <TableCell>
        <Textarea
          value={definition}
          onChange={(e) => setDefinition(e.target.value)}
          placeholder='정의'
          className='min-h-9 resize-none text-sm'
          rows={1}
        />
      </TableCell>
      <TableCell>
        <Input
          value={productGroup}
          onChange={(e) => setProductGroup(e.target.value)}
          placeholder='제품군 (선택)'
          className='text-sm'
        />
      </TableCell>
      <TableCell className='text-right'>
        <div className='flex justify-end gap-1.5'>
          <Button size='sm' variant='ghost' onClick={onCancel} className='h-7 text-xs'>
            취소
          </Button>
          <Button
            size='sm'
            onClick={handleSave}
            disabled={!term.trim() || !definition.trim()}
            className='h-7 text-xs'
          >
            <Check className='mr-1 size-3' />
            {initial ? '저장' : '추가'}
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

/* ─── Table Row ─── */

interface RowProps {
  item: GlossaryItem;
  editing: boolean;
  selected: boolean;
  onToggleSelect: (id: string) => void;
  onStartEdit: () => void;
  onUpdate: (
    id: string,
    data: { term?: string; definition?: string; product_group?: string | null },
  ) => void;
  onDelete: (id: string) => void;
  onCancelEdit: () => void;
}

function GlossaryRow({
  item,
  editing,
  selected,
  onToggleSelect,
  onStartEdit,
  onUpdate,
  onDelete,
  onCancelEdit,
}: RowProps) {
  if (editing) {
    return (
      <EditRow
        initial={{
          term: item.term,
          definition: item.definition,
          productGroup: item.product_group || '',
        }}
        onSave={(data) => {
          onUpdate(item.glossary_id, data);
          onCancelEdit();
        }}
        onCancel={onCancelEdit}
        autoFocus
      />
    );
  }

  return (
    <TableRow className='group hover:bg-muted/20'>
      <TableCell className='w-10 px-3'>
        <Checkbox checked={selected} onCheckedChange={() => onToggleSelect(item.glossary_id)} />
      </TableCell>
      <TableCell className='text-fg-primary truncate font-medium'>{item.term}</TableCell>
      <TableCell className='text-fg-secondary line-clamp-2 leading-relaxed'>
        {item.definition}
      </TableCell>
      <TableCell className='text-fg-muted truncate text-xs'>{item.product_group || '-'}</TableCell>
      <TableCell className='text-right'>
        <div className='flex justify-end gap-0.5 opacity-0 transition-opacity group-hover:opacity-100'>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size='icon-sm'
                variant='ghost'
                onClick={onStartEdit}
                className='text-fg-muted hover:text-fg-primary size-6'
              >
                <Pencil className='size-3' />
              </Button>
            </TooltipTrigger>
            <TooltipContent>수정</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size='icon-sm'
                variant='ghost'
                onClick={() => onDelete(item.glossary_id)}
                className='text-fg-muted hover:text-destructive size-6'
              >
                <Trash2 className='size-3' />
              </Button>
            </TooltipTrigger>
            <TooltipContent>삭제</TooltipContent>
          </Tooltip>
        </div>
      </TableCell>
    </TableRow>
  );
}

/* ─── Main Table ─── */

interface GlossaryTableProps {
  items: GlossaryItem[];
  onAdd: (data: GlossaryCreate) => void;
  onUpdate: (
    id: string,
    data: { term?: string; definition?: string; product_group?: string | null },
  ) => void;
  onDelete: (id: string) => void;
  onBulkDelete?: (ids: string[]) => void;
  generating?: boolean;
  onGenerate?: () => void;
}

export function GlossaryTable({
  items,
  onAdd,
  onUpdate,
  onDelete,
  onBulkDelete,
  generating,
  onGenerate,
}: GlossaryTableProps) {
  const [search, setSearch] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const filtered = useMemo(() => {
    if (!search.trim()) return items;
    const q = search.toLowerCase();
    return items.filter(
      (item) => item.term.toLowerCase().includes(q) || item.definition.toLowerCase().includes(q),
    );
  }, [items, search]);

  const allSelected =
    filtered.length > 0 && filtered.every((item) => selectedIds.has(item.glossary_id));
  const someSelected = filtered.some((item) => selectedIds.has(item.glossary_id)) && !allSelected;

  function handleSelectAll() {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map((item) => item.glossary_id)));
    }
  }

  function handleToggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function handleBulkDelete() {
    if (selectedIds.size === 0) return;
    onBulkDelete?.(Array.from(selectedIds));
    setSelectedIds(new Set());
  }

  return (
    <div className='flex flex-col'>
      {/* ─── Sticky Toolbar ─── */}
      <div className='bg-canvas-primary sticky top-0 z-10 flex flex-col gap-3 pb-3'>
        <div className='flex items-center justify-between gap-3'>
          {/* Search + Count */}
          <div className='flex items-center gap-3'>
            <div className='relative max-w-60'>
              <Search className='text-fg-muted absolute top-1/2 left-3 size-3.5 -translate-y-1/2' />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder='검색'
                className='h-8 pl-9 text-sm'
              />
            </div>
          </div>

          {/* Actions */}
          <div className='flex shrink-0 gap-1.5'>
            {selectedIds.size > 0 && (
              <Button
                size='sm'
                variant='outline'
                className='text-destructive hover:bg-destructive hover:text-destructive-foreground h-8 text-xs'
                onClick={handleBulkDelete}
              >
                <Trash2 className='size-3.5' />
                {selectedIds.size}건 삭제
              </Button>
            )}
            <Button
              size='sm'
              variant='outline'
              className='h-8 text-xs'
              onClick={() => {
                setAdding(true);
                setEditingId(null);
              }}
            >
              <Plus className='size-3.5' />
              추가
            </Button>
            {onGenerate && (
              <Button
                size='sm'
                variant='outline'
                className='h-8 text-xs'
                onClick={onGenerate}
                disabled={generating}
              >
                {generating ? <Spinner className='size-3.5' /> : <Sparkles className='size-3.5' />}
                {generating ? '생성 중...' : 'AI 생성'}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* ─── Table ─── */}
      <Table>
        <TableHeader>
          <TableRow className='bg-canvas-surface hover:bg-canvas-surface border-line-primary'>
            <TableHead className='w-10 px-3'>
              <Checkbox
                checked={allSelected}
                indeterminate={someSelected}
                onCheckedChange={handleSelectAll}
              />
            </TableHead>
            <TableHead className='text-fg-secondary w-[20%] text-xs font-semibold'>용어</TableHead>
            <TableHead className='text-fg-secondary w-[45%] text-xs font-semibold'>정의</TableHead>
            <TableHead className='text-fg-secondary w-[20%] text-xs font-semibold'>
              제품군
            </TableHead>
            <TableHead className='w-[10%]' />
          </TableRow>
        </TableHeader>
        <TableBody>
          {adding && (
            <EditRow
              onSave={(data) => {
                onAdd(data);
                setAdding(false);
              }}
              onCancel={() => setAdding(false)}
              autoFocus
            />
          )}

          {filtered.map((item) => (
            <GlossaryRow
              key={item.glossary_id}
              item={item}
              editing={editingId === item.glossary_id}
              selected={selectedIds.has(item.glossary_id)}
              onToggleSelect={handleToggleSelect}
              onStartEdit={() => {
                setEditingId(item.glossary_id);
                setAdding(false);
              }}
              onUpdate={onUpdate}
              onDelete={onDelete}
              onCancelEdit={() => setEditingId(null)}
            />
          ))}
        </TableBody>
      </Table>

      {/* ─── Empty States ─── */}
      {filtered.length === 0 && (
        <div className='flex flex-col items-center justify-center py-12 text-center'>
          <div className='bg-canvas-surface mb-4 flex size-16 items-center justify-center rounded-full'>
            {search ? (
              <Search className='text-fg-muted size-6' />
            ) : (
              <BookOpen className='text-fg-muted size-6' />
            )}
          </div>
          {search ? (
            <p className='text-fg-primary text-sm font-medium'>검색 결과가 없습니다</p>
          ) : (
            <>
              <p className='text-fg-primary text-sm font-medium'>아직 등록된 용어가 없습니다</p>
              <p className='text-fg-muted mt-1 text-sm'>
                상단의 추가 버튼이나 AI 생성을 사용하세요
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
