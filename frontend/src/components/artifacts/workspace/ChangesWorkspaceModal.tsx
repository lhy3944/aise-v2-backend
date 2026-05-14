'use client';

import { previewContent } from '@/components/artifacts/workspace/changePreview';
import { DiffViewer } from '@/components/artifacts/workspace/diff/DiffViewer';
import {
  PullRequestCreateActions,
  PullRequestCreateForm,
  type PullRequestCreateValues,
  type StagedChangeSummary,
} from '@/components/artifacts/workspace/PullRequestCreateForm';
import { StagedChangesTray } from '@/components/artifacts/workspace/StagedChangesTray';
import { Button } from '@/components/ui/button';
import { useOverlay } from '@/hooks/useOverlay';
import { artifactRecordService } from '@/services/artifact-record-service';
import { artifactService } from '@/services/artifact-service';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { usePrStore } from '@/stores/pr-store';
import { EMPTY_BUCKET, useStagingStore } from '@/stores/staging-store';
import type { ArtifactRecord, PullRequest } from '@/types/project';
import { ArrowLeft } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

interface ChangesWorkspaceModalProps {
  projectId: string;
}

export function ChangesWorkspaceModal({
  projectId,
}: ChangesWorkspaceModalProps) {
  const [records, setRecords] = useState<ArtifactRecord[]>([]);
  const [diffPr, setDiffPr] = useState<PullRequest | null>(null);
  const overlay = useOverlay();

  const unstaged = useStagingStore(
    (s) => s.byProject[projectId]?.unstaged ?? EMPTY_BUCKET.unstaged,
  );
  const staged = useStagingStore(
    (s) => s.byProject[projectId]?.staged ?? EMPTY_BUCKET.staged,
  );
  const stage = useStagingStore((s) => s.stage);
  const stageAll = useStagingStore((s) => s.stageAll);
  const unstage = useStagingStore((s) => s.unstage);
  const discardDraft = useStagingStore((s) => s.discardDraft);
  const discardStagedAction = useStagingStore((s) => s.discardStaged);
  const clearArtifact = useStagingStore((s) => s.clearArtifact);

  const openPRs = usePrStore((s) => s.openPRs);
  const prsLoading = usePrStore((s) => s.loading);
  const bumpPrRefresh = usePrStore((s) => s.bumpRefresh);

  const bumpRecordsRefresh = useArtifactRecordStore((s) => s.bumpRefresh);
  const bumpAllArtifacts = useArtifactRefreshStore((s) => s.bumpAll);

  const unstagedList = useMemo(() => Object.values(unstaged), [unstaged]);
  const stagedList = useMemo(() => Object.values(staged), [staged]);

  useEffect(() => {
    let cancelled = false;
    artifactRecordService
      .list(projectId)
      .then((res) => {
        if (!cancelled) setRecords(res.records);
      })
      .catch(() => {
        // 글로벌 핸들링
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const displayIdOf = useCallback(
    (artifactId: string) =>
      records.find((r) => r.artifact_id === artifactId)?.display_id,
    [records],
  );

  // ── Action handlers ────────────────────────────────────────────────────

  const handleStage = useCallback(
    (artifactId: string) => stage(projectId, artifactId),
    [stage, projectId],
  );
  const handleStageAll = useCallback(
    () => stageAll(projectId),
    [stageAll, projectId],
  );
  const handleUnstage = useCallback(
    (artifactId: string) => unstage(projectId, artifactId),
    [unstage, projectId],
  );
  const handleDiscardUnstaged = useCallback(
    (artifactId: string) => discardDraft(projectId, artifactId),
    [discardDraft, projectId],
  );
  const handleDiscardStaged = useCallback(
    (artifactId: string) => discardStagedAction(projectId, artifactId),
    [discardStagedAction, projectId],
  );

  const submitPullRequest = useCallback(
    async (values: PullRequestCreateValues, drafts: typeof stagedList) => {
      for (const draft of drafts) {
        await artifactService.update(projectId, draft.artifactId, {
          content: draft.content,
        });
        await artifactService.createPR(projectId, draft.artifactId, {
          title: values.title,
          description: values.description || null,
        });
        clearArtifact(projectId, draft.artifactId);
      }
      bumpPrRefresh();
      bumpRecordsRefresh();
      bumpAllArtifacts();
    },
    [
      projectId,
      clearArtifact,
      bumpPrRefresh,
      bumpRecordsRefresh,
      bumpAllArtifacts,
    ],
  );

  const handleCreatePR = useCallback(() => {
    if (stagedList.length === 0) return;

    const changes: StagedChangeSummary[] = stagedList.map((d) => ({
      artifactId: d.artifactId,
      displayId:
        d.displayLabel ?? displayIdOf(d.artifactId) ?? d.artifactId.slice(0, 8),
      contentPreview: previewContent(d.artifactKind, d.content),
    }));
    const defaultTitle =
      stagedList.length === 1
        ? `${changes[0].displayId} 편집`
        : `${changes.length}개 레코드 편집`;

    const onFormSubmit = async (values: PullRequestCreateValues) => {
      try {
        await submitPullRequest(values, stagedList);
        overlay.closeModal();
      } catch {
        // 글로벌 핸들링
      }
    };

    overlay.modal({
      title: 'PR 생성',
      description:
        'Staged 변경을 서버에 반영하고 Pull Request 를 엽니다. 머지 전까지 이 PR 을 통해 검토할 수 있습니다.',
      size: 'md',
      content: (
        <PullRequestCreateForm
          changes={changes}
          defaultTitle={defaultTitle}
          onSubmit={onFormSubmit}
        />
      ),
      footer: (
        <PullRequestCreateActions onCancel={() => overlay.closeModal()} />
      ),
    });
  }, [stagedList, displayIdOf, overlay, submitPullRequest]);

  const handleApprovePR = useCallback(
    async (prId: string) => {
      try {
        await artifactService.approvePR(prId);
        await artifactService.mergePR(prId);
        bumpPrRefresh();
        bumpRecordsRefresh();
        bumpAllArtifacts();
      } catch {
        // 글로벌 핸들링
      }
    },
    [bumpPrRefresh, bumpRecordsRefresh, bumpAllArtifacts],
  );

  const handleRejectPR = useCallback(
    async (prId: string) => {
      try {
        await artifactService.rejectPR(prId);
        bumpPrRefresh();
        bumpRecordsRefresh();
        bumpAllArtifacts();
      } catch {
        // 글로벌 핸들링
      }
    },
    [bumpPrRefresh, bumpRecordsRefresh, bumpAllArtifacts],
  );

  const handleShowDiff = useCallback((pr: PullRequest) => {
    setDiffPr(pr);
  }, []);

  // ── Diff 서브뷰 ──────────────────────────────────────────────────────

  if (diffPr) {
    const displayLabel =
      displayIdOf(diffPr.artifact_id) ?? diffPr.artifact_id.slice(0, 8);
    return (
      <div className='flex h-[60vh] min-h-[400px] flex-col gap-3'>
        <div className='flex shrink-0 items-center gap-2'>
          <Button
            variant='ghost'
            size='sm'
            className='h-7 gap-1 px-2 text-xs'
            onClick={() => setDiffPr(null)}
          >
            <ArrowLeft className='size-4' />
          </Button>
          <span className='text-fg-secondary text-xs font-medium'>
            {displayLabel}
          </span>
        </div>
        <div className='min-h-0 flex-1 overflow-hidden'>
          <DiffViewer
            headVersionId={diffPr.head_version_id}
            baseVersionId={diffPr.base_version_id ?? undefined}
          />
        </div>
      </div>
    );
  }

  // ── PR 리스트 뷰 ──────────────────────────────────────────────────────

  return (
    <StagedChangesTray
      unstaged={unstagedList}
      staged={stagedList}
      openPRs={openPRs}
      prsLoading={prsLoading}
      displayIdOf={displayIdOf}
      onStage={handleStage}
      onStageAll={handleStageAll}
      onUnstage={handleUnstage}
      onDiscardUnstaged={handleDiscardUnstaged}
      onDiscardStaged={handleDiscardStaged}
      onCreatePR={handleCreatePR}
      onApprovePR={handleApprovePR}
      onRejectPR={handleRejectPR}
      onShowDiff={handleShowDiff}
    />
  );
}
