/**
 * Agent metadata types (mirror of backend/src/agents/base.py::AgentCapability).
 *
 * Returned by GET /api/v1/agents and GET /api/v1/agents/{name}.
 */

export interface AgentCapability {
  name: string;
  description: string;
  triggers: string[];
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  requires_hitl: boolean;
  estimated_tokens: number;
  tags: string[];
}
