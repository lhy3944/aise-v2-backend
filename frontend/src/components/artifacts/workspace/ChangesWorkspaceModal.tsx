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
import { useOverlay } from '@/hooks/useOverlay';
import { artifactRecordService } from '@/services/artifact-record-service';
import { artifactService } from '@/services/artifact-service';
import { useArtifactRecordStore } from '@/stores/artifact-record-store';
import { useArtifactRefreshStore } from '@/stores/artifact-refresh-store';
import { usePrStore } from '@/stores/pr-store';
import { EMPTY_BUCKET, useStagingStore } from '@/stores/staging-store';
import type { ArtifactRecord, PullRequest } from '@/types/project';
import { useCallback, useEffect, useMemo, useState } from 'react';

interface ChangesWorkspaceModalProps {
  projectId: string;
}

/**
 * Unstaged / Staged / Open PRs 작업 트레이를 모달 내에서 자립형으로 운영.
 *
 * ArtifactRecordsPanel 이 한 번 overlay.modal() 로 마운트한 이후에는
 * 이 컴포넌트가 자체적으로:
 *   - 레코드 목록 조회 (displayIdOf + PR submit 시 content payload 유지용)
 *   - staging-store / pr-store 구독 (stage/unstage/discard/PR actions 즉시 반영)
 *   - 레코드 변경 후 artifact-record-store.bumpRefresh() 로 상위 패널 재조회 트리거
 *
 * 덕분에 modal 이 열려있는 동안에도 상위 ArtifactRecordsPanel 과 독립적으로
 * 최신 상태를 유지한다.
 */
export function ChangesWorkspaceModal({ projectId }: ChangesWorkspaceModalProps) {
  const [records, setRecords] = useState<ArtifactRecord[]>([]);
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

  // 레코드 조회 — displayId 레이블 + PR 생성 시 content payload 유지용
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
  const handleStageAll = useCallback(() => stageAll(projectId), [stageAll, projectId]);
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
      // staging-store v2: draft.content 가 이미 artifact_type 별 완전한 working
      // copy snapshot. 호출자(record/srs/design/testcase 화면)가 setDraft 시점에
      // 전체 payload 를 채워 넣어두므로 여기서는 그대로 PATCH 만 보낸다.
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
    [projectId, clearArtifact, bumpPrRefresh, bumpRecordsRefresh, bumpAllArtifacts],
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
      footer: <PullRequestCreateActions onCancel={() => overlay.closeModal()} />,
    });
  }, [stagedList, displayIdOf, overlay, submitPullRequest]);

  const handleApprovePR = useCallback(
    async (prId: string) => {
      try {
        await artifactService.approvePR(prId);
        bumpPrRefresh();
      } catch {
        // 글로벌 핸들링
      }
    },
    [bumpPrRefresh],
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

  const handleMergePR = useCallback(
    async (prId: string) => {
      try {
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

  const handleShowDiff = useCallback(
    (pr: PullRequest) => {
      const displayLabel = displayIdOf(pr.artifact_id) ?? pr.artifact_id.slice(0, 8);
      overlay.modal({
        title: `변경 내용 · ${displayLabel}`,
        size: 'lg',
        content: (
          <DiffViewer
            headVersionId={pr.head_version_id}
            baseVersionId={pr.base_version_id ?? undefined}
          />
        ),
      });
    },
    [displayIdOf, overlay],
  );

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
      onMergePR={handleMergePR}
      onShowDiff={handleShowDiff}
    />
  );
}
