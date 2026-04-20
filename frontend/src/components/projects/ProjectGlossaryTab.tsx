'use client';

import {
  GlossaryGenerateActions,
  GlossaryGenerateList,
  useGlossarySelection,
} from '@/components/projects/GlossaryGeneratePanel';
import { GlossaryTable } from '@/components/projects/GlossaryTable';
import { Modal } from '@/components/overlay/Modal';
import { ListSkeleton } from '@/components/shared/ListSkeleton';
import { useDeferredLoading } from '@/hooks/useDeferredLoading';
import { ApiError } from '@/lib/api';
import { showToast } from '@/lib/toast';
import { glossaryService } from '@/services/glossary-service';
import { useOverlayStore } from '@/stores/overlay-store';
import { useReadinessStore } from '@/stores/readiness-store';
import type { GlossaryCreate, GlossaryItem } from '@/types/project';
import { useCallback, useEffect, useState } from 'react';

interface ProjectGlossaryTabProps {
  projectId: string;
}

export function ProjectGlossaryTab({ projectId }: ProjectGlossaryTabProps) {
  const { showConfirm } = useOverlayStore();
  const invalidateReadiness = useReadinessStore((s) => s.invalidate);

  const [items, setItems] = useState<GlossaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const showSkeleton = useDeferredLoading(loading);
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState<GlossaryCreate[]>([]);
  const [adding, setAdding] = useState(false);

  const { selected, toggle, toggleAll, reset } = useGlossarySelection(generated.length);

  const fetchGlossary = useCallback(async () => {
    setLoading(true);
    try {
      const data = await glossaryService.list(projectId);
      setItems(data.glossary);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '용어 목록을 불러올 수 없습니다.';
      showToast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchGlossary();
  }, [fetchGlossary]);

  async function handleAdd(data: GlossaryCreate) {
    try {
      const created = await glossaryService.create(projectId, data);
      setItems((prev) => [...prev, created]);
      invalidateReadiness();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '용어 추가에 실패했습니다.';
      showToast.error(msg);
    }
  }

  async function handleUpdate(
    glossaryId: string,
    data: { term?: string; definition?: string; product_group?: string | null },
  ) {
    try {
      const updated = await glossaryService.update(projectId, glossaryId, data);
      setItems((prev) => prev.map((item) => (item.glossary_id === glossaryId ? updated : item)));
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '용어 수정에 실패했습니다.';
      showToast.error(msg);
    }
  }

  function handleDelete(glossaryId: string) {
    showConfirm({
      title: '용어 삭제',
      description: '이 용어를 삭제하시겠습니까?',
      variant: 'destructive',
      onConfirm: async () => {
        try {
          await glossaryService.delete(projectId, glossaryId);
          setItems((prev) => prev.filter((item) => item.glossary_id !== glossaryId));
          invalidateReadiness();
        } catch (err) {
          const msg = err instanceof ApiError ? err.message : '삭제에 실패했습니다.';
          showToast.error(msg);
        }
      },
    });
  }

  function handleBulkDelete(ids: string[]) {
    showConfirm({
      title: '용어 일괄 삭제',
      description: `선택한 ${ids.length}개 용어를 삭제하시겠습니까?`,
      variant: 'destructive',
      onConfirm: async () => {
        try {
          await Promise.all(ids.map((id) => glossaryService.delete(projectId, id)));
          setItems((prev) => prev.filter((item) => !ids.includes(item.glossary_id)));
          invalidateReadiness();
          showToast.success(`${ids.length}개 용어가 삭제되었습니다.`);
        } catch (err) {
          const msg = err instanceof ApiError ? err.message : '일괄 삭제에 실패했습니다.';
          showToast.error(msg);
        }
      },
    });
  }

  async function handleGenerate() {
    setGenerating(true);
    setGenerated([]);
    try {
      const result = await glossaryService.extract(projectId);
      const newItems = result.candidates.map((c) => ({
        term: c.term,
        definition: c.definition,
        synonyms: c.synonyms,
        abbreviations: c.abbreviations,
      }));
      setGenerated(newItems);
      reset(newItems.length);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '자동 생성에 실패했습니다.';
      showToast.error(msg);
    } finally {
      setGenerating(false);
    }
  }

  async function handleApplyGenerated() {
    const selectedItems = generated.filter((_, i) => selected.has(i));
    if (selectedItems.length === 0) return;

    setAdding(true);
    try {
      const created = await Promise.all(
        selectedItems.map((item) => glossaryService.create(projectId, item)),
      );
      setItems((prev) => [...prev, ...created]);
      setGenerated([]);
      invalidateReadiness();
      showToast.success(`${created.length}개 용어가 추가되었습니다.`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '용어 추가에 실패했습니다.';
      showToast.error(msg);
    } finally {
      setAdding(false);
    }
  }

  if (showSkeleton) {
    return <ListSkeleton />;
  }

  if (loading) return null;

  return (
    <div className='flex flex-col gap-4'>
      <GlossaryTable
        items={items}
        onAdd={handleAdd}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
        onBulkDelete={handleBulkDelete}
        generating={generating}
        onGenerate={handleGenerate}
      />

      {/* AI 생성 결과 Modal */}
      <Modal
        open={generated.length > 0}
        onOpenChange={(open) => {
          if (!open) setGenerated([]);
        }}
        title={`AI 제안 용어 (${generated.length}건)`}
        description='추가할 용어를 선택하세요.'
        size='lg'
        footer={
          <GlossaryGenerateActions
            selectedCount={selected.size}
            onApply={handleApplyGenerated}
            onCancel={() => setGenerated([])}
            isLoading={adding}
          />
        }
      >
        <GlossaryGenerateList
          generated={generated}
          selected={selected}
          onToggle={toggle}
          onToggleAll={toggleAll}
        />
      </Modal>
    </div>
  );
}
