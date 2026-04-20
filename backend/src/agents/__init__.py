"""Agent plugin layer.

Public surface:
- BaseAgent, AgentCapability — contract
- register_agent              — decorator for plugin registration
- get_agent / list_agents     — runtime lookup
- load_builtin_agents()       — call once at startup
"""

from src.agents.base import AgentCapability, BaseAgent
from src.agents.registry import (
    find_by_tag,
    get_agent,
    list_agents,
    list_capabilities,
    load_builtin_agents,
    register_agent,
    try_get_agent,
)

__all__ = [
    "AgentCapability",
    "BaseAgent",
    "find_by_tag",
    "get_agent",
    "list_agents",
    "list_capabilities",
    "load_builtin_agents",
    "register_agent",
    "try_get_agent",
]
