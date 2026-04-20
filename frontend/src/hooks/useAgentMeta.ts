/**
 * Agent registry metadata hooks (DESIGN §10.4).
 *
 * `useAgentMeta()` lists every registered agent.
 * `useAgentMeta(name)` fetches a single agent's capability.
 *
 * The registry is effectively static during a session (agents register at
 * backend startup), so we disable revalidation aggressively — consumers
 * can `mutate()` if they need a refresh.
 */

import { useFetch } from '@/hooks/useFetch';
import type { AgentCapability } from '@/types/agents';

export function useAgentList() {
  return useFetch<AgentCapability[]>('/api/v1/agents', {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
    dedupingInterval: 60_000,
  });
}

export function useAgent(name: string | null | undefined) {
  return useFetch<AgentCapability>(
    name ? `/api/v1/agents/${name}` : null,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 60_000,
    },
  );
}

/** Convenience default export — returns the list hook. */
export default useAgentList;
