import { api } from '@/lib/api';
import type {
  Artifact,
  ArtifactKind,
  ArtifactListResponse,
  ArtifactVersionListResponse,
  DiffResult,
  JsonObject,
  PullRequest,
  PullRequestCreate,
  PullRequestListResponse,
  PullRequestStatus,
  WorkingStatus,
} from '@/types/project';

function projectBase(projectId: string) {
  return `/api/v1/projects/${projectId}`;
}

export interface ArtifactUpdatePayload {
  content?: JsonObject;
  title?: string | null;
}

/**
 * 공통 Artifact Governance API 클라이언트.
 *
 * record-specific CRUD(섹션/지식문서 enrich)는 artifact-record-service 사용.
 * 여기서는 타입-무관 공통 동작(content PATCH, PR 라이프사이클)만 다룬다.
 */
export const artifactService = {
  // ── Artifact ─────────────────────────────────────────────────────────
  list: (
    projectId: string,
    params?: { artifact_type?: ArtifactKind; working_status?: WorkingStatus },
  ) => {
    const query = new URLSearchParams();
    if (params?.artifact_type) query.set('artifact_type', params.artifact_type);
    if (params?.working_status) query.set('working_status', params.working_status);
    const qs = query.toString();
    return api.get<ArtifactListResponse>(
      `${projectBase(projectId)}/artifacts${qs ? `?${qs}` : ''}`,
    );
  },

  get: (projectId: string, artifactId: string) =>
    api.get<Artifact>(`${projectBase(projectId)}/artifacts/${artifactId}`),

  update: (projectId: string, artifactId: string, data: ArtifactUpdatePayload) =>
    api.patch<Artifact>(`${projectBase(projectId)}/artifacts/${artifactId}`, data),

  listVersions: (projectId: string, artifactId: string) =>
    api.get<ArtifactVersionListResponse>(
      `${projectBase(projectId)}/artifacts/${artifactId}/versions`,
    ),

  // ── PullRequest ──────────────────────────────────────────────────────
  createPR: (projectId: string, artifactId: string, data: PullRequestCreate) =>
    api.post<PullRequest>(
      `${projectBase(projectId)}/artifacts/${artifactId}/prs`,
      data,
    ),

  listPRs: (projectId: string, status?: PullRequestStatus) => {
    const query = status ? `?status=${status}` : '';
    return api.get<PullRequestListResponse>(`${projectBase(projectId)}/prs${query}`);
  },

  approvePR: (prId: string) =>
    api.post<PullRequest>(`/api/v1/prs/${prId}/approve`),

  rejectPR: (prId: string, reason?: string) =>
    api.post<PullRequest>(`/api/v1/prs/${prId}/reject`, reason ? { reason } : {}),

  mergePR: (prId: string) =>
    api.post<PullRequest>(`/api/v1/prs/${prId}/merge`),

  // ── Diff ─────────────────────────────────────────────────────────────
  diff: (versionId: string, against?: string) => {
    const query = against ? `?against=${against}` : '';
    return api.get<DiffResult>(`/api/v1/versions/${versionId}/diff${query}`);
  },
};
