'use client';

import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ListSkeleton } from '@/components/shared/ListSkeleton';
import { RequirementTable } from '@/components/requirements/RequirementTable';
import { RequirementInput } from '@/components/requirements/RequirementInput';
import { ReviewModal } from '@/components/requirements/ReviewModal';
import { requirementService } from '@/services/requirement-service';
import { sectionService } from '@/services/section-service';
import { useOverlayStore } from '@/stores/overlay-store';
import { useReview } from '@/hooks/useReview';
import { ApiError } from '@/lib/api';
import { showToast } from '@/lib/toast';
import { Spinner } from '@/components/ui/spinner';
import { Save, ClipboardCheck } from 'lucide-react';
import type { Requirement, RequirementType, Section } from '@/types/project';

interface RequirementsArtifactProps {
  projectId: string;
}

export function RequirementsArtifact({ projectId }: RequirementsArtifactProps) {
  const { showConfirm } = useOverlayStore();

  const [activeTab, setActiveTab] = useState<RequirementType>('fr');
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchRequirements = useCallback(async () => {
    setLoading(true);
    try {
      const [reqData, secData] = await Promise.all([
        requirementService.list(projectId),
        sectionService.list(projectId),
      ]);
      setRequirements(reqData.requirements);
      setSections(secData.sections);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '요구사항 목록을 불러올 수 없습니다.';
      showToast.error(msg);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchRequirements();
  }, [fetchRequirements]);

  // Review hook
  const review = useReview({ projectId });

  const handleRunReview = () => {
    const includedIds = requirements.filter((r) => r.is_selected).map((r) => r.requirement_id);
    if (includedIds.length === 0) {
      showToast.warning('Include된 요구사항이 없습니다.');
      return;
    }
    review.runReview(includedIds);
  };

  // --- Requirement Handlers ---

  async function handleAdd(text: string) {
    try {
      const created = await requirementService.create(projectId, {
        type: activeTab,
        original_text: text,
      });
      setRequirements((prev) => [...prev, created]);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '요구사항 추가에 실패했습니다.';
      showToast.error(msg);
    }
  }

  async function handleUpdate(requirementId: string, originalText: string) {
    try {
      const updated = await requirementService.update(projectId, requirementId, {
        original_text: originalText,
      });
      setRequirements((prev) =>
        prev.map((r) => (r.requirement_id === requirementId ? updated : r)),
      );
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '요구사항 수정에 실패했습니다.';
      showToast.error(msg);
    }
  }

  function handleDelete(requirementId: string) {
    showConfirm({
      title: '요구사항 삭제',
      description: '이 요구사항을 삭제하시겠습니까?',
      variant: 'destructive',
      onConfirm: async () => {
        try {
          await requirementService.delete(projectId, requirementId);
          setRequirements((prev) => prev.filter((r) => r.requirement_id !== requirementId));
        } catch (err) {
          const msg = err instanceof ApiError ? err.message : '삭제에 실패했습니다.';
          showToast.error(msg);
        }
      },
    });
  }

  async function handleToggleSelect(requirementId: string, selected: boolean) {
    setRequirements((prev) =>
      prev.map((r) => (r.requirement_id === requirementId ? { ...r, is_selected: selected } : r)),
    );
    try {
      await requirementService.updateSelection(projectId, {
        requirement_ids: [requirementId],
        is_selected: selected,
      });
    } catch {
      setRequirements((prev) =>
        prev.map((r) =>
          r.requirement_id === requirementId ? { ...r, is_selected: !selected } : r,
        ),
      );
    }
  }

  async function handleSave() {
    setSaving(true);
    try {
      const result = await requirementService.save(projectId);
      showToast.success(`버전 ${result.version}이 저장되었습니다. (${result.saved_count}건)`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '저장에 실패했습니다.';
      showToast.error(msg);
    } finally {
      setSaving(false);
    }
  }

  async function handleReorder(orderedIds: string[]) {
    const orderedSet = new Set(orderedIds);
    setRequirements((prev) => {
      const others = prev.filter((r) => !orderedSet.has(r.requirement_id));
      const reordered = orderedIds
        .map((id) => prev.find((r) => r.requirement_id === id))
        .filter(Boolean) as Requirement[];
      return [...others, ...reordered];
    });
    try {
      await requirementService.reorder(projectId, { ordered_ids: orderedIds });
      await fetchRequirements();
    } catch {
      await fetchRequirements();
    }
  }

  // --- Section Handlers ---

  async function handleSectionCreate(name: string) {
    try {
      const created = await sectionService.create(projectId, { name, type: activeTab });
      setSections((prev) => [...prev, created]);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '섹션 추가에 실패했습니다.';
      showToast.error(msg);
    }
  }

  async function handleSectionRename(sectionId: string, name: string) {
    try {
      const updated = await sectionService.update(projectId, sectionId, { name });
      setSections((prev) => prev.map((s) => (s.section_id === sectionId ? updated : s)));
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '섹션 이름 변경에 실패했습니다.';
      showToast.error(msg);
    }
  }

  function handleSectionDelete(sectionId: string) {
    showConfirm({
      title: '섹션 삭제',
      description: '이 섹션을 삭제하시겠습니까? 소속된 요구사항은 미분류로 이동됩니다.',
      variant: 'destructive',
      onConfirm: async () => {
        try {
          await sectionService.delete(projectId, sectionId);
          setSections((prev) => prev.filter((s) => s.section_id !== sectionId));
          setRequirements((prev) =>
            prev.map((r) => (r.section_id === sectionId ? { ...r, section_id: null } : r)),
          );
        } catch (err) {
          const msg = err instanceof ApiError ? err.message : '섹션 삭제에 실패했습니다.';
          showToast.error(msg);
        }
      },
    });
  }

  async function handleSectionReorder(orderedIds: string[]) {
    setSections((prev) => {
      const sectionMap = new Map(prev.map((s) => [s.section_id, s]));
      const reordered = orderedIds.map((id) => sectionMap.get(id)).filter(Boolean) as Section[];
      const others = prev.filter((s) => !orderedIds.includes(s.section_id));
      return [...reordered, ...others];
    });
    try {
      await sectionService.reorder(projectId, { ordered_ids: orderedIds });
    } catch {
      await fetchRequirements();
    }
  }

  async function handleMoveToSection(requirementId: string, sectionId: string | null) {
    setRequirements((prev) =>
      prev.map((r) => (r.requirement_id === requirementId ? { ...r, section_id: sectionId } : r)),
    );
    try {
      await requirementService.update(projectId, requirementId, {
        section_id: sectionId ?? '',
      });
    } catch {
      await fetchRequirements();
    }
  }

  // --- Tab labels ---
  const tabCounts = {
    fr: requirements.filter((r) => r.type === 'fr').length,
    qa: requirements.filter((r) => r.type === 'qa').length,
    constraints: requirements.filter((r) => r.type === 'constraints').length,
  };

  // --- 공통 테이블 렌더링 ---
  function renderTable(type: RequirementType) {
    const typeReqs = requirements.filter((r) => r.type === type);
    const typeSections = sections.filter((s) => s.type === type);
    const typeSelectedIds = typeReqs.filter((r) => r.is_selected).map((r) => r.requirement_id);
    const typeAllSelected = typeReqs.length > 0 && typeSelectedIds.length === typeReqs.length;
    const typeSomeSelected = typeSelectedIds.length > 0 && !typeAllSelected;

    async function handleTypeSelectAll() {
      const newSelected = !typeAllSelected;
      const ids = typeReqs.map((r) => r.requirement_id);
      setRequirements((prev) =>
        prev.map((r) => (ids.includes(r.requirement_id) ? { ...r, is_selected: newSelected } : r)),
      );
      try {
        await requirementService.updateSelection(projectId, {
          requirement_ids: ids,
          is_selected: newSelected,
        });
      } catch {
        setRequirements((prev) =>
          prev.map((r) =>
            ids.includes(r.requirement_id) ? { ...r, is_selected: !newSelected } : r,
          ),
        );
      }
    }

    return loading ? (
      <ListSkeleton rows={4} rowHeight='h-12' header={false} />
    ) : (
      <RequirementTable
        requirements={typeReqs}
        sections={typeSections}
        allSelected={typeAllSelected}
        someSelected={typeSomeSelected}
        onSelectAll={handleTypeSelectAll}
        onToggleSelect={handleToggleSelect}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
        onReorder={handleReorder}
        onMoveToSection={handleMoveToSection}
        onSectionCreate={handleSectionCreate}
        onSectionRename={handleSectionRename}
        onSectionDelete={handleSectionDelete}
        onSectionReorder={handleSectionReorder}
      />
    );
  }

  return (
    <div className='flex h-full flex-col overflow-hidden'>
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as RequirementType)}
        className='flex flex-1 flex-col overflow-hidden'
      >
        {/* Header: Tabs + Actions */}
        <div className='shrink-0 px-4 pt-3'>
          <div className='flex items-center justify-between gap-2'>
            <TabsList className='shrink-0'>
              <TabsTrigger value='fr'>FR ({tabCounts.fr})</TabsTrigger>
              <TabsTrigger value='qa'>QA ({tabCounts.qa})</TabsTrigger>
              <TabsTrigger value='constraints'>CON ({tabCounts.constraints})</TabsTrigger>
            </TabsList>

            <div className='flex shrink-0 gap-1'>
              <Button
                size='sm'
                variant='ghost'
                onClick={handleRunReview}
                disabled={review.isReviewing}
                className='h-7 px-2 text-xs'
              >
                {review.isReviewing ? (
                  <Spinner size='size-3' />
                ) : (
                  <ClipboardCheck className='size-3' />
                )}
              </Button>
              <Button
                size='sm'
                variant='ghost'
                onClick={handleSave}
                disabled={saving}
                className='h-7 px-2 text-xs'
              >
                <Save className='size-3' />
              </Button>
            </div>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className='flex-1 overflow-y-auto px-4 pb-4'>
          {/* Input Area */}
          <div className='mt-3'>
            <RequirementInput type={activeTab} onAdd={handleAdd} />
          </div>

          {/* Requirement Table */}
          <div className='mt-3'>
            {(['fr', 'qa', 'constraints'] as RequirementType[]).map((type) => (
              <TabsContent key={type} value={type} className='mt-0'>
                {renderTable(type)}
              </TabsContent>
            ))}
          </div>
        </div>
      </Tabs>

      {/* Review Modal */}
      <ReviewModal
        open={review.isModalOpen}
        onOpenChange={review.setIsModalOpen}
        reviewData={review.reviewData}
        isLoading={review.isReviewing}
      />
    </div>
  );
}
