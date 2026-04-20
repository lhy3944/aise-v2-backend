"""Agent registry exposure (DESIGN.md §10.4)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.agents import list_capabilities, try_get_agent
from src.agents.base import AgentCapability

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("", response_model=list[AgentCapability])
async def list_registered_agents() -> list[AgentCapability]:
    """Return every registered agent's capability descriptor."""
    return list_capabilities()


@router.get("/{agent_name}", response_model=AgentCapability)
async def get_agent_detail(agent_name: str) -> AgentCapability:
    agent = try_get_agent(agent_name)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"agent '{agent_name}' not found")
    return agent.capability
