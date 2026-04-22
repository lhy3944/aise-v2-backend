/**
 * Agent SSE event types — single source of truth for the frontend.
 *
 * Mirrors backend/src/schemas/events.py and docs/events.md.
 * Changes here MUST be applied in all three files in the same PR.
 */

// ---------- Phase 1 events ----------

export interface TokenEvent {
  type: 'token';
  data: { text: string };
}

export interface ToolCallEvent {
  type: 'tool_call';
  data: {
    tool_call_id: string;
    name: string;
    arguments: Record<string, unknown>;
    agent?: string;
  };
}

export interface ToolResultEvent {
  type: 'tool_result';
  data: {
    tool_call_id: string;
    name: string;
    status: 'success' | 'error';
    duration_ms?: number;
    result?: unknown;
  };
}

export type FinishReason =
  | 'stop'
  | 'tool_calls'
  | 'length'
  | 'content_filter'
  | 'interrupt'
  | 'error';

export interface DoneEvent {
  type: 'done';
  data: { finish_reason: FinishReason };
}

export interface ErrorEvent {
  type: 'error';
  data: {
    message: string;
    code?: string;
    recoverable?: boolean;
  };
}

// ---------- Phase 2 events ----------

export type PlanStepStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped';

export interface PlanStep {
  agent: string;
  status: PlanStepStatus;
  started_at?: string;
  completed_at?: string;
  result_summary?: string;
}

export interface PlanUpdateEvent {
  type: 'plan_update';
  data: {
    plan: PlanStep[];
    current_step?: number;
  };
}

export type ArtifactType =
  | 'srs'
  | 'design'
  | 'testcase'
  | 'requirement_list'
  | 'records';

export interface ArtifactCreatedEvent {
  type: 'artifact_created';
  data: {
    artifact_id: string;
    artifact_type: ArtifactType;
    title: string;
    project_id: string;
    version?: string;
  };
}

export interface SourceRef {
  ref: number;
  document_id: string;
  document_name: string;
  chunk_index: number;
  file_type?: string;
  content_preview?: string;
  score?: number;
}

export interface SourcesEvent {
  type: 'sources';
  data: {
    sources: SourceRef[];
    agent?: string;
  };
}

// ---------- Phase 3 events (HITL) ----------

export interface ClarifyOption {
  value: string;
  label: string;
  description?: string;
}

export interface ClarifyData {
  kind: 'clarify';
  interrupt_id: string;
  question: string;
  options?: ClarifyOption[];
  allow_custom: boolean;
  context?: Record<string, unknown>;
}

export interface ConfirmImpact {
  label: string;
  detail: string;
}

export type ConfirmSeverity = 'info' | 'warning' | 'danger';

export interface ConfirmActions {
  approve: string;
  reject: string;
  modify?: string;
}

export interface ConfirmData {
  kind: 'confirm';
  interrupt_id: string;
  title: string;
  description: string;
  impact?: ConfirmImpact[];
  severity: ConfirmSeverity;
  actions: ConfirmActions;
}

export interface DecisionOption {
  id: string;
  label: string;
  default?: boolean;
}

export interface DecisionData {
  kind: 'decision';
  interrupt_id: string;
  question: string;
  options: DecisionOption[];
  min_selection?: number;
  max_selection?: number;
}

export type HitlData = ClarifyData | ConfirmData | DecisionData;

export interface InterruptEvent {
  type: 'interrupt';
  data: HitlData;
}

// ---------- Discriminated union ----------

export type AgentStreamEvent =
  | TokenEvent
  | ToolCallEvent
  | ToolResultEvent
  | PlanUpdateEvent
  | InterruptEvent
  | ArtifactCreatedEvent
  | SourcesEvent
  | DoneEvent
  | ErrorEvent;

// ---------- Resume request body ----------

export interface ResumeRequest {
  interrupt_id: string;
  response: Record<string, unknown>;
}

// ---------- Type guards ----------

export const isTokenEvent = (e: AgentStreamEvent): e is TokenEvent =>
  e.type === 'token';
export const isToolCallEvent = (e: AgentStreamEvent): e is ToolCallEvent =>
  e.type === 'tool_call';
export const isToolResultEvent = (e: AgentStreamEvent): e is ToolResultEvent =>
  e.type === 'tool_result';
export const isPlanUpdateEvent = (e: AgentStreamEvent): e is PlanUpdateEvent =>
  e.type === 'plan_update';
export const isInterruptEvent = (e: AgentStreamEvent): e is InterruptEvent =>
  e.type === 'interrupt';
export const isArtifactCreatedEvent = (
  e: AgentStreamEvent,
): e is ArtifactCreatedEvent => e.type === 'artifact_created';
export const isSourcesEvent = (e: AgentStreamEvent): e is SourcesEvent =>
  e.type === 'sources';
export const isDoneEvent = (e: AgentStreamEvent): e is DoneEvent =>
  e.type === 'done';
export const isErrorEvent = (e: AgentStreamEvent): e is ErrorEvent =>
  e.type === 'error';
