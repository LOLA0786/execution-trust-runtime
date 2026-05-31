"""
Core package for Execution Trust Runtime.
Exports key components (additive only).
"""

from .vault.private_vault import vault, vault_checkpoint, VaultCheckpointError, Verdict
from .approval_gate import ApprovalGate
from .approval_token import ApprovalToken, generate_token, verify_token
from .llm.grok_client import grok_client, GrokClient
from .memory.vector_memory import VectorMemory, memory
from .memory.reflection import reflection
from .policy_loader import policy_loader
from .metrics import (
    record_vault_block,
    record_approval,
    observe_trust_score,
    observe_agent_latency,
    observe_approval_wait,
)

__all__ = [
    "vault",
    "vault_checkpoint",
    "VaultCheckpointError",
    "Verdict",
    "ApprovalGate",
    "ApprovalToken",
    "generate_token",
    "verify_token",
    "grok_client",
    "GrokClient",
    "VectorMemory",
    "memory",
    "reflection",
    "policy_loader",
    "record_vault_block",
    "record_approval",
    "observe_trust_score",
    "observe_agent_latency",
    "observe_approval_wait",
]
