'use client';

import {
  Pencil,
  Trash2,
  GripVertical,
  Check,
  X,
  ChevronRight,
  ChevronDown,
  Plus,
  FolderPlus,
} from 'lucide-react';
import { useState, useRef, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { Requirement, Section } from '@/types/project';

interface RequirementTableProps {
  requirements: Requirement[];
  sections: Section[];
  allSelected: boolean;
  someSelected: boolean;
  onSelectAll: () => void;
  onToggleSelect: (id: string, selected: boolean) => void;
  onUpdate: (id: string, originalText: string) => void;
  onDelete: (id: string) => void;
  onReorder: (orderedIds: string[]) => void;
  onMoveToSection: (requirementId: string, sectionId: string | null) => void;
  onSectionCreate: (name: string) => void;
  onSectionRename: (sectionId: string, name: string) => void;
  onSectionDelete: (sectionId: string) => void;
  onSectionReorder: (orderedIds: string[]) => void;
}

export function RequirementTable({
  requirements,
  sections,
  allSelected,
  someSelected,
  onSelectAll,
  onToggleSelect,
  onUpdate,
  onDelete,
  onReorder,
  onMoveToSection,
  onSectionCreate,
  onSectionRename,
  onSectionDelete,
  onSectionReorder,
}: RequirementTableProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [editingSectionName, setEditingSectionName] = useState('');
  const [isAddingSection, setIsAddingSection] = useState(false);
  const [newSectionName, setNewSectionName] = useState('');
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [dragOverSectionId, setDragOverSectionId] = useState<string | null>(null);
  const dragItemRef = useRef<number | null>(null);
  const dragSectionRef = useRef<string | null>(null);
  const dragSourceSectionRef = useRef<string | null>(null);

  // 섹션별 요구사항 그룹핑
  const { grouped, uncategorized } = useMemo(() => {
    const grouped = new Map<string, Requirement[]>();
    const uncategorized: Requirement[] = [];

    for (const section of sections) {
      grouped.set(section.section_id, []);
    }

    for (const req of requirements) {
      if (req.section_id && grouped.has(req.section_id)) {
        grouped.get(req.section_id)!.push(req);
      } else {
        uncategorized.push(req);
      }
    }

    // 각 섹션 내 order_index로 정렬
    for (const reqs of grouped.values()) {
      reqs.sort((a, b) => a.order_index - b.order_index);
    }
    uncategorized.sort((a, b) => a.order_index - b.order_index);

    return { grouped, uncategorized };
  }, [requirements, sections]);

  const hasSections = sections.length > 0;

  // --- 요구사항 인라인 편집 ---
  function startEdit(req: Requirement) {
    setEditingId(req.requirement_id);
    setEditText(req.refined_text || req.original_text);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditText('');
  }

  function saveEdit(id: string) {
    if (!editText.trim()) return;
    onUpdate(id, editText.trim());
    setEditingId(null);
    setEditText('');
  }

  // --- 섹션 접기/펼치기 ---
  function toggleCollapse(sectionId: string) {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) next.delete(sectionId);
      else next.add(sectionId);
      return next;
    });
  }

  function collapseAll() {
    setCollapsedSections(new Set(sections.map((s) => s.section_id)));
  }

  function expandAll() {
    setCollapsedSections(new Set());
  }

  // --- 섹션 이름 편집 ---
  function startSectionEdit(section: Section) {
    setEditingSectionId(section.section_id);
    setEditingSectionName(section.name);
  }

  function cancelSectionEdit() {
    setEditingSectionId(null);
    setEditingSectionName('');
  }

  function saveSectionEdit(sectionId: string) {
    if (!editingSectionName.trim()) return;
    onSectionRename(sectionId, editingSectionName.trim());
    setEditingSectionId(null);
    setEditingSectionName('');
  }

  // --- 섹션 추가 ---
  function startAddSection() {
    setIsAddingSection(true);
    setNewSectionName('');
  }

  function cancelAddSection() {
    setIsAddingSection(false);
    setNewSectionName('');
  }

  function saveNewSection() {
    if (!newSectionName.trim()) return;
    onSectionCreate(newSectionName.trim());
    setIsAddingSection(false);
    setNewSectionName('');
  }

  // --- 요구사항 드래그 앤 드롭 (섹션 내부) ---
  const handleDragStart = useCallback((index: number, sectionId: string | null) => {
    dragItemRef.current = index;
    dragSourceSectionRef.current = sectionId;
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent, index: number, sectionId: string | null) => {
      e.preventDefault();
      // 같은 섹션 내에서만 순서 변경
      if (dragSourceSectionRef.current === sectionId) {
        setDragOverIndex(index);
      }
      setDragOverSectionId(sectionId);
    },
    [],
  );

  const handleDrop = useCallback(
    (dropIndex: number, sectionId: string | null) => {
      const dragIndex = dragItemRef.current;
      const sourceSectionId = dragSourceSectionRef.current;

      if (dragIndex === null) {
        setDragOverIndex(null);
        setDragOverSectionId(null);
        return;
      }

      // 다른 섹션으로 이동
      if (sourceSectionId !== sectionId) {
        const sourceReqs =
          sourceSectionId === null ? uncategorized : grouped.get(sourceSectionId) || [];
        const draggedReq = sourceReqs[dragIndex];
        if (draggedReq) {
          onMoveToSection(draggedReq.requirement_id, sectionId);
        }
      } else if (dragIndex !== dropIndex) {
        // 같은 섹션 내 순서 변경
        const sectionReqs = sectionId === null ? uncategorized : grouped.get(sectionId) || [];
        const reordered = [...sectionReqs];
        const [moved] = reordered.splice(dragIndex, 1);
        reordered.splice(dropIndex, 0, moved);
        onReorder(reordered.map((r) => r.requirement_id));
      }

      setDragOverIndex(null);
      setDragOverSectionId(null);
      dragItemRef.current = null;
      dragSourceSectionRef.current = null;
    },
    [uncategorized, grouped, onMoveToSection, onReorder],
  );

  const handleDragEnd = useCallback(() => {
    setDragOverIndex(null);
    setDragOverSectionId(null);
    dragItemRef.current = null;
    dragSourceSectionRef.current = null;
  }, []);

  // --- 섹션 드래그 앤 드롭 ---
  const handleSectionDragStart = useCallback((sectionId: string) => {
    dragSectionRef.current = sectionId;
  }, []);

  const handleSectionDragOver = useCallback((e: React.DragEvent, sectionId: string) => {
    e.preventDefault();
    if (dragSectionRef.current && dragSectionRef.current !== sectionId) {
      setDragOverSectionId(sectionId);
    }
  }, []);

  const handleSectionDrop = useCallback(
    (targetSectionId: string) => {
      const sourceSectionId = dragSectionRef.current;
      if (!sourceSectionId || sourceSectionId === targetSectionId) {
        setDragOverSectionId(null);
        dragSectionRef.current = null;
        return;
      }

      const ids = sections.map((s) => s.section_id);
      const fromIdx = ids.indexOf(sourceSectionId);
      const toIdx = ids.indexOf(targetSectionId);
      if (fromIdx === -1 || toIdx === -1) return;

      const reordered = [...ids];
      const [moved] = reordered.splice(fromIdx, 1);
      reordered.splice(toIdx, 0, moved);
      onSectionReorder(reordered);

      setDragOverSectionId(null);
      dragSectionRef.current = null;
    },
    [sections, onSectionReorder],
  );

  const handleSectionDragEnd = useCallback(() => {
    setDragOverSectionId(null);
    dragSectionRef.current = null;
  }, []);

  // --- 요구사항 행 렌더링 ---
  function renderRow(req: Requirement, index: number, sectionId: string | null) {
    return (
      <div
        key={req.requirement_id}
        draggable={editingId !== req.requirement_id}
        onDragStart={() => handleDragStart(index, sectionId)}
        onDragOver={(e) => handleDragOver(e, index, sectionId)}
        onDrop={() => handleDrop(index, sectionId)}
        onDragEnd={handleDragEnd}
        className={cn(
          'border-line-subtle group grid grid-cols-[40px_90px_1fr_80px_72px] items-start gap-0 border-b px-3 py-2.5 transition-colors last:border-b-0',
          dragOverIndex === index && dragOverSectionId === sectionId && 'bg-accent-primary/10',
          req.is_selected && 'bg-accent-primary/5',
        )}
      >
        {/* Drag Handle */}
        <div className='flex cursor-grab items-center justify-center opacity-0 transition-opacity group-hover:opacity-60 active:cursor-grabbing'>
          <GripVertical className='text-fg-muted size-4' />
        </div>

        {/* Display ID */}
        <div className='text-fg-muted font-mono text-sm'>{req.display_id}</div>

        {/* Description */}
        <div className='min-w-0 pr-3'>
          {editingId === req.requirement_id ? (
            <div className='flex flex-col gap-2'>
              <Textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className='min-h-16 resize-none text-sm'
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Escape') cancelEdit();
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) saveEdit(req.requirement_id);
                }}
              />
              <div className='flex gap-1.5'>
                <Button
                  size='xs'
                  onClick={() => saveEdit(req.requirement_id)}
                  disabled={!editText.trim()}
                >
                  <Check className='size-3' /> 저장
                </Button>
                <Button size='xs' variant='ghost' onClick={cancelEdit}>
                  <X className='size-3' /> 취소
                </Button>
              </div>
            </div>
          ) : (
            <p className='text-fg-primary text-sm break-words whitespace-pre-wrap'>
              {req.refined_text || req.original_text}
            </p>
          )}
        </div>

        {/* Include Checkbox */}
        <div className='flex justify-center'>
          <Checkbox
            checked={req.is_selected}
            onCheckedChange={(checked) => onToggleSelect(req.requirement_id, checked as boolean)}
          />
        </div>

        {/* Actions */}
        {editingId !== req.requirement_id && (
          <div className='flex justify-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100'>
            <Button size='icon-xs' variant='ghost' onClick={() => startEdit(req)} title='수정'>
              <Pencil className='size-3.5' />
            </Button>
            <Button
              size='icon-xs'
              variant='ghost'
              onClick={() => onDelete(req.requirement_id)}
              title='삭제'
              className='text-destructive hover:text-destructive'
            >
              <Trash2 className='size-3.5' />
            </Button>
          </div>
        )}
      </div>
    );
  }

  // --- 빈 상태 ---
  if (requirements.length === 0 && !isAddingSection) {
    return (
      <div className='text-fg-muted py-12 text-center text-sm'>
        아직 요구사항이 없습니다. 위에서 입력하여 추가하세요.
      </div>
    );
  }

  return (
    <div className='space-y-0'>
      {/* 섹션 컨트롤 바 */}
      <div className='mb-2 flex items-center justify-between'>
        <div className='flex items-center gap-2'>
          <Button size='xs' variant='outline' onClick={startAddSection}>
            <FolderPlus className='size-3.5' />
            섹션 추가
          </Button>
          {hasSections && (
            <>
              <Button size='xs' variant='ghost' onClick={expandAll}>
                전체 펼치기
              </Button>
              <Button size='xs' variant='ghost' onClick={collapseAll}>
                전체 접기
              </Button>
            </>
          )}
        </div>
      </div>

      {/* 새 섹션 추가 입력 */}
      {isAddingSection && (
        <div className='border-accent-primary/30 bg-accent-primary/5 mb-2 flex items-center gap-2 rounded-lg border px-3 py-2'>
          <FolderPlus className='text-fg-muted size-4 shrink-0' />
          <input
            type='text'
            value={newSectionName}
            onChange={(e) => setNewSectionName(e.target.value)}
            placeholder='섹션 이름을 입력하세요'
            className='flex-1 bg-transparent text-sm outline-none'
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') saveNewSection();
              if (e.key === 'Escape') cancelAddSection();
            }}
          />
          <Button size='xs' onClick={saveNewSection} disabled={!newSectionName.trim()}>
            <Check className='size-3' /> 추가
          </Button>
          <Button size='xs' variant='ghost' onClick={cancelAddSection}>
            <X className='size-3' /> 취소
          </Button>
        </div>
      )}

      <div className='border-line-subtle overflow-hidden rounded-lg border'>
        {/* Header */}
        <div className='bg-muted/50 text-fg-muted border-line-subtle grid grid-cols-[40px_90px_1fr_80px_72px] items-start gap-0 border-b px-3 py-2.5 text-xs font-medium tracking-wide uppercase'>
          <div />
          <div>No.</div>
          <div>Description</div>
          <div className='text-center'>Include</div>
          <div className='text-center'>Actions</div>
        </div>

        {/* 섹션별 렌더링 */}
        {sections.map((section) => {
          const sectionReqs = grouped.get(section.section_id) || [];
          const isCollapsed = collapsedSections.has(section.section_id);
          const isEditingSection = editingSectionId === section.section_id;

          return (
            <div key={section.section_id}>
              {/* 섹션 헤더 */}
              <div
                draggable={!isEditingSection}
                onDragStart={() => handleSectionDragStart(section.section_id)}
                onDragOver={(e) => handleSectionDragOver(e, section.section_id)}
                onDrop={() => handleSectionDrop(section.section_id)}
                onDragEnd={handleSectionDragEnd}
                className={cn(
                  'bg-muted/40 border-line-subtle group/section flex cursor-pointer items-center gap-2 border-b px-3 py-2',
                  dragOverSectionId === section.section_id &&
                    dragSectionRef.current &&
                    'bg-accent-primary/10',
                )}
              >
                <div className='flex cursor-grab items-center justify-center opacity-0 transition-opacity group-hover/section:opacity-60 active:cursor-grabbing'>
                  <GripVertical className='text-fg-muted size-4' />
                </div>

                <button
                  onClick={() => toggleCollapse(section.section_id)}
                  className='flex items-center gap-1'
                >
                  {isCollapsed ? (
                    <ChevronRight className='text-fg-muted size-4' />
                  ) : (
                    <ChevronDown className='text-fg-muted size-4' />
                  )}
                </button>

                {isEditingSection ? (
                  <div className='flex flex-1 items-center gap-2'>
                    <input
                      type='text'
                      value={editingSectionName}
                      onChange={(e) => setEditingSectionName(e.target.value)}
                      className='border-fg-muted/30 flex-1 border-b bg-transparent text-sm font-medium outline-none'
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') saveSectionEdit(section.section_id);
                        if (e.key === 'Escape') cancelSectionEdit();
                      }}
                    />
                    <Button
                      size='icon-xs'
                      variant='ghost'
                      onClick={() => saveSectionEdit(section.section_id)}
                    >
                      <Check className='size-3.5' />
                    </Button>
                    <Button size='icon-xs' variant='ghost' onClick={cancelSectionEdit}>
                      <X className='size-3.5' />
                    </Button>
                  </div>
                ) : (
                  <>
                    <span
                      className='text-fg-primary flex-1 text-sm font-medium'
                      onClick={() => toggleCollapse(section.section_id)}
                    >
                      {section.name}
                    </span>
                    <span className='text-fg-muted text-xs'>{sectionReqs.length}개</span>
                    <div className='flex items-center gap-0.5 opacity-0 transition-opacity group-hover/section:opacity-100'>
                      <Button
                        size='icon-xs'
                        variant='ghost'
                        onClick={(e) => {
                          e.stopPropagation();
                          startSectionEdit(section);
                        }}
                        title='섹션 이름 변경'
                      >
                        <Pencil className='size-3' />
                      </Button>
                      <Button
                        size='icon-xs'
                        variant='ghost'
                        onClick={(e) => {
                          e.stopPropagation();
                          onSectionDelete(section.section_id);
                        }}
                        title='섹션 삭제'
                        className='text-destructive hover:text-destructive'
                      >
                        <Trash2 className='size-3' />
                      </Button>
                    </div>
                  </>
                )}
              </div>

              {/* 섹션 내 요구사항 */}
              {!isCollapsed &&
                sectionReqs.map((req, index) => renderRow(req, index, section.section_id))}

              {/* 섹션 내 빈 상태 (드롭 영역) */}
              {!isCollapsed && sectionReqs.length === 0 && (
                <div
                  onDragOver={(e) => handleDragOver(e, 0, section.section_id)}
                  onDrop={() => handleDrop(0, section.section_id)}
                  className={cn(
                    'text-fg-muted border-line-subtle border-b px-3 py-4 text-center text-xs',
                    dragOverSectionId === section.section_id &&
                      !dragSectionRef.current &&
                      'bg-accent-primary/10',
                  )}
                >
                  요구사항을 이 섹션으로 드래그하세요
                </div>
              )}
            </div>
          );
        })}

        {/* 미분류 요구사항 */}
        {uncategorized.length > 0 && (
          <div>
            {hasSections && (
              <div className='bg-muted/20 border-line-subtle flex items-center gap-2 border-b px-3 py-2'>
                <span className='text-fg-muted text-sm font-medium'>미분류</span>
                <span className='text-fg-muted text-xs'>{uncategorized.length}개</span>
              </div>
            )}
            {uncategorized.map((req, index) => renderRow(req, index, null))}
          </div>
        )}

        {/* Footer: Select All */}
        <div className='bg-muted/30 border-line-subtle flex items-center gap-2 border-t px-4 py-2'>
          <Checkbox
            checked={allSelected}
            indeterminate={someSelected}
            onCheckedChange={onSelectAll}
          />
          <span className='text-fg-muted text-xs'>{allSelected ? '전체 해제' : '전체 선택'}</span>
        </div>
      </div>
    </div>
  );
}
