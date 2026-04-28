// --- Enums ---

export type RequirementType = 'fr' | 'qa' | 'constraints' | 'other';

export type ProjectModule = 'requirements' | 'design' | 'testcase';

export type ProjectStatus = 'active' | 'archived';

// --- Project ---

export interface ProjectReadiness {
  knowledge: number;
  glossary: number;
  sections: number;
  is_ready: boolean;
}

export interface Project {
  project_id: string;
  name: string;
  description: string | null;
  domain: string | null;
  product_type: string | null;
  modules: ProjectModule[];
  member_count: number;
  status: ProjectStatus;
  readiness: ProjectReadiness | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
  domain?: string | null;
  product_type?: string | null;
  modules: ProjectModule[];
}

export interface ProjectUpdate {
  name?: string | null;
  description?: string | null;
  domain?: string | null;
  product_type?: string | null;
  modules?: ProjectModule[] | null;
}

/** 프로젝트 hard delete 시 영향받을 데이터 카운트 미리보기. */
export interface ProjectDeletePreview {
  project_id: string;
  project_name: string;
  knowledge_documents: number;
  knowledge_files_bytes: number;
  sessions: number;
  session_messages: number;
  artifacts: number;
  artifact_versions: number;
  pull_requests: number;
  glossary_items: number;
  requirement_sections: number;
}

export interface ProjectListResponse {
  projects: Project[];
}

// --- Requirement ---

// --- Section (요구사항 그룹) ---

export interface Section {
  section_id: string;
  name: string;
  type: string;
  description: string | null;
  output_format_hint: string | null;
  is_default: boolean;
  is_active: boolean;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface SectionCreate {
  name: string;
  type: string;
  description?: string | null;
  output_format_hint?: string | null;
}

export interface SectionUpdate {
  name?: string | null;
  description?: string | null;
  output_format_hint?: string | null;
}

export interface SectionReorderRequest {
  ordered_ids: string[];
}

export interface SectionListResponse {
  sections: Section[];
}

export interface Requirement {
  requirement_id: string;
  display_id: string;
  order_index: number;
  type: RequirementType;
  original_text: string;
  refined_text: string | null;
  is_selected: boolean;
  status: string;
  section_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface RequirementReorderRequest {
  ordered_ids: string[];
}

export interface RequirementCreate {
  type: RequirementType;
  original_text: string;
  section_id?: string | null;
}

export interface RequirementUpdate {
  original_text?: string | null;
  refined_text?: string | null;
  is_selected?: boolean | null;
  section_id?: string | null;
}

export interface RequirementListResponse {
  requirements: Requirement[];
}

export interface RequirementSelectionUpdate {
  requirement_ids: string[];
  is_selected: boolean;
}

export interface RequirementSaveResponse {
  version: number;
  saved_count: number;
  saved_at: string;
}

// --- Glossary ---

export interface GlossaryItem {
  glossary_id: string;
  term: string;
  definition: string;
  product_group: string | null;
  synonyms: string[];
  abbreviations: string[];
  section_tags: string[];
  source_document_id: string | null;
  source_document_name: string | null;
  is_auto_extracted: boolean;
  is_approved: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface GlossaryCreate {
  term: string;
  definition: string;
  product_group?: string | null;
  synonyms?: string[];
  abbreviations?: string[];
  section_tags?: string[];
  source_document_id?: string | null;
}

export interface GlossaryUpdate {
  term?: string | null;
  definition?: string | null;
  product_group?: string | null;
  synonyms?: string[] | null;
  abbreviations?: string[] | null;
  section_tags?: string[] | null;
}

export interface GlossaryListResponse {
  glossary: GlossaryItem[];
}

export interface GlossaryGenerateResponse {
  generated_glossary: GlossaryCreate[];
}

export interface GlossaryExtractedItem {
  term: string;
  definition: string;
  synonyms: string[];
  abbreviations: string[];
  source_document_id: string | null;
  source_document_name: string | null;
}

export interface GlossaryExtractResponse {
  candidates: GlossaryExtractedItem[];
}

// --- Review ---

export interface ReviewRequest {
  requirement_ids: string[];
}

export interface ReviewIssue {
  issue_id: string;
  type: 'conflict' | 'duplicate';
  description: string;
  related_requirements: string[];
  hint: string; // 해결 힌트 1줄
}

export interface ReviewSummary {
  total_issues: number;
  conflicts: number;
  duplicates: number;
  ready_for_next: boolean;
  feedback: string;
}

export interface ReviewResponse {
  review_id: string;
  issues: ReviewIssue[];
  summary: ReviewSummary;
}

export interface LatestReviewResponse {
  review_id: string;
  created_at: string;
  reviewed_requirement_ids: string[];
  issues: ReviewIssue[];
  summary: ReviewSummary;
}

// --- Project Settings ---

export interface ProjectSettings {
  llm_model: string;
  language: string;
  export_format: string;
  diagram_tool: string;
}

export interface ProjectSettingsUpdate {
  llm_model?: string | null;
  language?: string | null;
  export_format?: string | null;
  diagram_tool?: string | null;
}

// --- Knowledge Document ---

export type KnowledgeDocumentFileType = 'pdf' | 'md' | 'txt';
export type KnowledgeDocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface KnowledgeDocument {
  document_id: string;
  project_id: string;
  name: string;
  file_type: KnowledgeDocumentFileType;
  size_bytes: number;
  status: KnowledgeDocumentStatus;
  is_active: boolean;
  error_message: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocumentListResponse {
  documents: KnowledgeDocument[];
  total: number;
}

export interface KnowledgeDocumentPreview {
  document_id: string;
  name: string;
  file_type: KnowledgeDocumentFileType;
  preview_text: string;
  total_characters: number;
}

// --- SRS ---

export interface SrsSection {
  section_id: string | null;
  title: string;
  content: string;
  order_index: number;
}

export interface SrsDocument {
  srs_id: string; // ArtifactVersion.id (version 단위 식별자)
  artifact_id: string; // Artifact.id (staging/PR 워크플로우 키)
  project_id: string;
  version: number;
  status: string;
  error_message: string | null;
  sections: SrsSection[];
  based_on_records: { artifact_ids?: string[] } | null;
  based_on_documents: { documents?: { id: string; name: string }[] } | null;
  source_artifact_versions: SourceArtifactVersions | null;
  created_at: string;
}

export interface SrsListResponse {
  documents: SrsDocument[];
}

// --- Design (artifact_type='design' 의 도메인 뷰, SRS 와 동일 패턴) ---
export interface DesignSection {
  section_id: string | null;
  title: string;
  content: string;
  order_index: number;
}

export interface DesignDocument {
  design_id: string; // ArtifactVersion.id (version 단위 식별자)
  artifact_id: string; // Artifact.id (staging/PR 워크플로우 키)
  project_id: string;
  version: number;
  status: string;
  error_message: string | null;
  sections: DesignSection[];
  based_on_srs: { version_id?: string; version_number?: number } | null;
  source_artifact_versions: SourceArtifactVersions | null;
  created_at: string;
}

export interface DesignListResponse {
  documents: DesignDocument[];
}

// --- ArtifactRecord (artifact_type='record' 의 도메인 뷰) ---

export type ArtifactRecordStatus = 'draft' | 'approved' | 'excluded';

export interface ArtifactRecord {
  artifact_id: string;
  project_id: string;
  section_id: string | null;
  section_name: string | null;
  content: string;
  display_id: string;
  source_document_id: string | null;
  source_document_name: string | null;
  source_location: string | null;
  confidence_score: number | null;
  status: ArtifactRecordStatus;
  is_auto_extracted: boolean;
  order_index: number;
  /** record 도 ArtifactVersion 체인 보유. null/0 이면 머지된 버전 없음. */
  current_version_number: number | null;
  created_at: string;
  updated_at: string;
}

export interface ArtifactRecordCreate {
  content: string;
  section_id?: string | null;
  source_document_id?: string | null;
  source_location?: string | null;
  confidence_score?: number | null;
}

export interface ArtifactRecordUpdate {
  content?: string | null;
  section_id?: string | null;
}

export interface ArtifactRecordListResponse {
  records: ArtifactRecord[];
  total: number;
}

export interface ArtifactRecordExtractedItem {
  content: string;
  section_id: string | null;
  section_name: string | null;
  source_document_id: string | null;
  source_document_name: string | null;
  source_location: string | null;
  confidence_score: number | null;
}

export interface ArtifactRecordExtractResponse {
  candidates: ArtifactRecordExtractedItem[];
}

// --- Artifact Governance (Git-like: Unstaged/Staged/PR/Merge) ---
export type JsonObject = { [key: string]: unknown };

export type ArtifactKind = 'record' | 'srs' | 'design' | 'testcase';
export type WorkingStatus = 'clean' | 'dirty' | 'staged';
export type LifecycleStatus = 'active' | 'archived' | 'deleted';
export type PullRequestStatus =
  | 'open'
  | 'approved'
  | 'rejected'
  | 'merged'
  | 'superseded';
export type DependencyType = 'derives_from' | 'references' | 'covers';
export type ChangeAction =
  | 'created'
  | 'edited'
  | 'staged'
  | 'pr_opened'
  | 'pr_approved'
  | 'pr_merged'
  | 'pr_rejected'
  | 'reverted';

// Record/SRS/Design/TC 각각의 JSON payload shape은 타입별로 다르다.
// 공용 Artifact 타입은 payload를 제네릭으로 유지.
export interface Artifact<T = JsonObject> {
  artifact_id: string;
  project_id: string;
  artifact_type: ArtifactKind;
  display_id: string;
  title: string | null;
  content: T;
  working_status: WorkingStatus;
  lifecycle_status: LifecycleStatus;
  current_version_id: string | null;
  current_version_number: number | null;
  /** Phase E lineage — current_version_id 의 source 참조. */
  current_source_artifact_versions: SourceArtifactVersions | null;
  open_pr_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ArtifactListResponse {
  artifacts: Artifact[];
  total: number;
}

/** Phase E lineage entry — 이 version 을 만들 때 입력으로 사용한 다른 artifact 의 version. */
export interface SourceArtifactVersionRef {
  artifact_id: string;
  /** 입력으로 쓴 ArtifactVersion.id (= SRS/Design 화면의 selectedXxxId 와 동일).
   *  record source 처럼 lineage 가 PR 머지 후 채워지는 경우엔 미존재할 수 있음. */
  version_id?: string;
  version_number?: number;
  /** SRS 의 특정 섹션을 참조한 경우 등 — TC->SRS 케이스 */
  section_id?: string | null;
}

// --- Phase F: Impact / Stale ---
export interface StaleReason {
  source_artifact_id: string;
  source_artifact_type: string;
  source_display_id: string | null;
  referenced_version: number | null;
  current_version: number | null;
  section_id: string | null;
}

export interface ImpactedArtifact {
  artifact_id: string;
  artifact_type: string;
  display_id: string;
  current_version_number: number | null;
  stale_reasons: StaleReason[];
}

export interface ImpactResponse {
  stale: ImpactedArtifact[];
}

export interface ImpactApplyRequest {
  /** 비어 있으면 전체 stale 을 대상으로 함. */
  artifact_ids: string[];
}

export interface ImpactApplyEntry {
  artifact_id: string;
  artifact_type: string;
  display_id: string | null;
  new_version_id: string | null;
  new_version_number: number | null;
  error: string | null;
  skipped_reason: string | null;
}

export interface ImpactApplyResponse {
  regenerated: ImpactApplyEntry[];
  skipped: ImpactApplyEntry[];
  failed: ImpactApplyEntry[];
}

/** kind 별 lineage 엔트리 묶음. */
export interface SourceArtifactVersions {
  record?: SourceArtifactVersionRef[];
  srs?: SourceArtifactVersionRef[];
  design?: SourceArtifactVersionRef[];
  testcase?: SourceArtifactVersionRef[];
}

export interface ArtifactVersion<T = JsonObject> {
  version_id: string;
  artifact_id: string;
  artifact_type: ArtifactKind;
  version_number: number;
  parent_version_id: string | null;
  snapshot: T;
  content_hash: string;
  commit_message: string;
  author_id: string;
  committed_at: string;
  merged_from_pr_id: string | null;
  source_artifact_versions: SourceArtifactVersions | null;
}

export interface ArtifactVersionListResponse {
  versions: ArtifactVersion[];
}

// --- Diff ---

export type DiffFormat = 'unified' | 'deepdiff';

export interface DiffHunk {
  op: 'equal' | 'add' | 'delete';
  text: string;
}

export interface DiffFieldEntry {
  field_path: string;
  kind: 'added' | 'removed' | 'modified' | 'unchanged';
  before?: unknown;
  after?: unknown;
  hunks?: DiffHunk[];
}

export interface DiffResult {
  format: DiffFormat;
  base_version_id: string | null;
  head_version_id: string;
  entries: DiffFieldEntry[];
  unified_text: string | null;
}

// --- PullRequest ---

export interface PullRequest {
  pr_id: string;
  project_id: string;
  artifact_id: string;
  artifact_type: ArtifactKind;
  base_version_id: string | null;
  head_version_id: string;
  status: PullRequestStatus;
  title: string;
  description: string | null;
  author_id: string;
  reviewer_id: string | null;
  created_at: string;
  reviewed_at: string | null;
  merged_at: string | null;
  auto_generated: boolean;
}

export interface PullRequestListResponse {
  pull_requests: PullRequest[];
  total: number;
}

export interface PullRequestCreate {
  title: string;
  description?: string | null;
}

// --- ChangeEvent (audit log) ---

export interface ChangeEvent {
  event_id: string;
  project_id: string;
  artifact_id: string | null;
  pr_id: string | null;
  version_id: string | null;
  action: ChangeAction;
  actor: string;
  diff_summary: JsonObject | null;
  impact_summary: JsonObject | null;
  occurred_at: string;
}

// --- Impact graph ---

export type ImpactReason =
  | 'upstream_version_bumped'
  | 'upstream_status_changed'
  | 'upstream_deleted';

export interface ImpactedArtifactRef {
  artifact_id: string;
  artifact_type: ArtifactKind;
  display_id: string;
  reason: ImpactReason;
  pinned_version_number: number | null;
}

export interface ImpactResponse {
  source_artifact_id: string;
  impacted: ImpactedArtifactRef[];
}

// --- Staging buffers (client-side only) ---
//
// Unstaged/Staged edits는 서버에 도달하지 않은 로컬 버퍼.
// sessionStorage에 persist되어 새로고침을 방어한다.
export interface ArtifactDraft<T = JsonObject> {
  artifact_id: string | null; // null = 신규 (아직 서버 ID 없음)
  local_id: string; // 로컬 고유 식별자 (unstaged 관리용)
  artifact_type: ArtifactKind;
  change_type: 'create' | 'update' | 'delete';
  base_version_id: string | null;
  content: T;
  title?: string | null;
  updated_at: string;
}

// --- Readiness ---

export interface ReadinessItem {
  label: string;
  count: number;
  sufficient: boolean;
}

export interface ReadinessResponse {
  knowledge: ReadinessItem;
  glossary: ReadinessItem;
  sections: ReadinessItem;
  is_ready: boolean;
}

// --- Common ---

export interface ErrorDetail {
  code: string;
  message: string;
  detail?: string | null;
}

export interface ErrorResponse {
  error: ErrorDetail;
}
