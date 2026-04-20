'use client';

import { useCallback, useEffect, useState, use } from 'react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ListSkeleton } from '@/components/shared/ListSkeleton';
import { RequirementTable } from '@/components/requirements/RequirementTable';
import { RequirementInput } from '@/components/requirements/RequirementInput';
import { RefineCompare } from '@/components/requirements/RefineCompare';
import { SuggestionPanel } from '@/components/requirements/SuggestionPanel';
import { ChatPanel } from '@/components/requirements/ChatPanel';
import { requirementService } from '@/services/requirement-service';
import { sectionService } from '@/services/section-service';
import { assistService } from '@/services/assist-service';
import { ReviewModal } from '@/components/requirements/ReviewModal';
import { useOverlayStore } from '@/stores/overlay-store';
import { useReview } from '@/hooks/useReview';
import { ApiError } from '@/lib/api';
import { showToast } from '@/lib/toast';
import { Spinner } from '@/components/ui/spinner';
import { Save, Sparkles, List, MessageSquare, ClipboardCheck } from 'lucide-react';
import type {
  Requirement,
  RequirementType,
  RefineResponse,
  Section,
  Suggestion,
} from '@/types/project';

interface Props {
  params: Promise<{ id: string }>;
}

export default function RequirementsPage({ params }: Props) {
  const { id: projectId } = use(params);
  const { showConfirm } = useOverlayStore();

  const [mode, setMode] = useState<'structured' | 'chat'>('structured');
  const [activeTab, setActiveTab] = useState<RequirementType>('fr');
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // AI Assist state
  const [refineResult, setRefineResult] = useState<RefineResponse | null>(null);
  const [isRefining, setIsRefining] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isSuggesting, setIsSuggesting] = useState(false);

  const filtered = requirements.filter((r) => r.type === activeTab);
  const filteredSections = sections.filter((s) => s.type === activeTab);
  const selectedIds = filtered.filter((r) => r.is_selected).map((r) => r.requirement_id);
  const allSelected = filtered.length > 0 && selectedIds.length === filtered.length;
  const someSelected = selectedIds.length > 0 && !allSelected;

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

  // --- Review handler: Include된 요구사항만 전달 ---
  const handleRunReview = () => {
    const includedIds = requirements.filter((r) => r.is_selected).map((r) => r.requirement_id);

    if (includedIds.length === 0) {
      showToast.warning(
        'Include된 요구사항이 없습니다. 요구사항을 추가하거나 Include 상태를 확인해주세요.',
      );
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

  async function handleSelectAll() {
    const newSelected = !allSelected;
    const ids = filtered.map((r) => r.requirement_id);
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
        prev.map((r) => (ids.includes(r.requirement_id) ? { ...r, is_selected: !newSelected } : r)),
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

  // --- Reorder ---
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
      const created = await sectionService.create(projectId, {
        name,
        type: activeTab,
      });
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
          // 섹션에 속했던 요구사항의 section_id를 null로 업데이트
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
    // Optimistic update
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
    // Optimistic update
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

  // --- AI Assist ---

  async function handleRefine(text: string) {
    setIsRefining(true);
    setRefineResult(null);
    try {
      const result = await assistService.refine(projectId, {
        text,
        type: activeTab,
      });
      setRefineResult(result);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'AI 정제에 실패했습니다.';
      showToast.error(msg);
    } finally {
      setIsRefining(false);
    }
  }

  async function handleAcceptRefine(result: RefineResponse) {
    try {
      const created = await requirementService.create(projectId, {
        type: result.type,
        original_text: result.original_text,
      });
      const updated = await requirementService.update(projectId, created.requirement_id, {
        refined_text: result.refined_text,
      });
      setRequirements((prev) => [...prev, updated]);
      setRefineResult(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '요구사항 추가에 실패했습니다.';
      showToast.error(msg);
    }
  }

  async function handleSuggest() {
    if (selectedIds.length === 0) {
      showToast.warning('먼저 요구사항을 선택하세요.');
      return;
    }
    setIsSuggesting(true);
    setSuggestions([]);
    try {
      const result = await assistService.suggest(projectId, {
        requirement_ids: selectedIds,
      });
      setSuggestions(result.suggestions);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'AI 제안에 실패했습니다.';
      showToast.error(msg);
    } finally {
      setIsSuggesting(false);
    }
  }

  async function handleAcceptSuggestion(suggestion: Suggestion) {
    try {
      const created = await requirementService.create(projectId, {
        type: suggestion.type,
        original_text: suggestion.text,
      });
      setRequirements((prev) => [...prev, created]);
      setSuggestions((prev) => prev.filter((s) => s !== suggestion));
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : '제안 수락에 실패했습니다.';
      showToast.error(msg);
    }
  }

  function handleRejectSuggestion(index: number) {
    setSuggestions((prev) => prev.filter((_, i) => i !== index));
  }

  // --- Chat mode callback ---
  function handleChatRequirementAdded(requirement: Requirement) {
    setRequirements((prev) => [...prev, requirement]);
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
    <div className='mx-auto max-w-4xl px-6 py-6'>
      {/* Mode Toggle + Review */}
      <div className='mb-4 flex items-center justify-between'>
        <div className='border-line-subtle bg-canvas-primary flex w-fit items-center gap-1 rounded-lg border p-1'>
          <button
            onClick={() => setMode('structured')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === 'structured'
                ? 'bg-primary text-primary-foreground'
                : 'text-fg-muted hover:text-fg-primary hover:bg-muted'
            }`}
          >
            <List className='size-4' />
            구조화 모드
          </button>
          <button
            onClick={() => setMode('chat')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === 'chat'
                ? 'bg-primary text-primary-foreground'
                : 'text-fg-muted hover:text-fg-primary hover:bg-muted'
            }`}
          >
            <MessageSquare className='size-4' />
            대화 모드
          </button>
        </div>
      </div>

      {mode === 'chat' ? (
        /* Chat Mode */
        <div className='flex flex-col gap-6'>
          <ChatPanel projectId={projectId} onRequirementAdded={handleChatRequirementAdded} />

          {/* 현재 요구사항 현황 */}
          <div>
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as RequirementType)}>
              <div className='mb-4 flex items-center justify-between'>
                <TabsList>
                  <TabsTrigger value='fr'>FR ({tabCounts.fr})</TabsTrigger>
                  <TabsTrigger value='qa'>QA ({tabCounts.qa})</TabsTrigger>
                  <TabsTrigger value='constraints'>
                    Constraints ({tabCounts.constraints})
                  </TabsTrigger>
                </TabsList>
              </div>

              {(['fr', 'qa', 'constraints'] as RequirementType[]).map((type) => (
                <TabsContent key={type} value={type}>
                  {renderTable(type)}
                </TabsContent>
              ))}
            </Tabs>
          </div>
        </div>
      ) : (
        /* Structured Mode */
        <Tabs
          value={activeTab}
          onValueChange={(v) => {
            setActiveTab(v as RequirementType);
            setRefineResult(null);
            setSuggestions([]);
          }}
        >
          <div className='mb-4 flex items-center justify-between'>
            <TabsList>
              <TabsTrigger value='fr'>FR ({tabCounts.fr})</TabsTrigger>
              <TabsTrigger value='qa'>QA ({tabCounts.qa})</TabsTrigger>
              <TabsTrigger value='constraints'>Constraints ({tabCounts.constraints})</TabsTrigger>
            </TabsList>

            <div className='flex gap-2'>
              <Button
                size='sm'
                variant='outline'
                onClick={handleRunReview}
                disabled={review.isReviewing}
              >
                {review.isReviewing ? (
                  <Spinner size='size-3.5' />
                ) : (
                  <ClipboardCheck className='size-3.5' />
                )}
                {review.isReviewing ? '리뷰 중...' : '리뷰'}
              </Button>
              <Button
                size='sm'
                variant='outline'
                onClick={handleSuggest}
                disabled={selectedIds.length === 0 || isSuggesting}
              >
                <Sparkles className='size-3.5' />
                {isSuggesting ? 'AI 제안 중...' : 'AI 제안'}
              </Button>
              <Button size='sm' onClick={handleSave} disabled={saving}>
                <Save className='size-3.5' />
                {saving ? '저장 중...' : '저장'}
              </Button>
            </div>
          </div>

          {/* Input Area */}
          <div className='mb-4'>
            <RequirementInput
              type={activeTab}
              onAdd={handleAdd}
              onRefine={handleRefine}
              isRefining={isRefining}
            />
          </div>

          {/* Refine Compare */}
          {refineResult && (
            <div className='mb-4'>
              <RefineCompare
                result={refineResult}
                onAccept={handleAcceptRefine}
                onReject={() => setRefineResult(null)}
              />
            </div>
          )}

          {/* Suggestion Panel */}
          {suggestions.length > 0 && (
            <div className='mb-4'>
              <SuggestionPanel
                suggestions={suggestions}
                onAccept={handleAcceptSuggestion}
                onReject={handleRejectSuggestion}
                onClose={() => setSuggestions([])}
              />
            </div>
          )}

          {/* Requirement Table */}
          {(['fr', 'qa', 'constraints'] as RequirementType[]).map((type) => (
            <TabsContent key={type} value={type}>
              {renderTable(type)}
            </TabsContent>
          ))}
        </Tabs>
      )}

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
