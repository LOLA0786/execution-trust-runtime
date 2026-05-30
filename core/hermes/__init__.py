"""
Hermes package for multi-agent orchestration.
Exports the central HermesOrchestrator for role-based routing, structured outputs,
and pipeline coordination across the 3 agents with PrivateVault gates.
"""
from .orchestrator import HermesOrchestrator, hermes, AgentOutput

__all__ = ["HermesOrchestrator", "hermes", "AgentOutput"]
