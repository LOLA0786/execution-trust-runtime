"""
shared/schemas/event_schemas.py

Pydantic event schemas for Execution Trust Runtime.
Extends PrivateVault models for pipeline events, agent runs, and audit logging.
"""
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

from core.vault.private_vault import Verdict


class EventType(str, Enum):
    INPUT = "input"
    RETRIEVAL = "retrieval"
    REFLECTION = "reflection"
    RESEARCH = "research"
    DECISION = "decision"
    APPROVAL = "approval"
    EXECUTION = "execution"
    POST_CHECKPOINT = "post_checkpoint"
    HANDOFF = "handoff"


class PipelineEvent(BaseModel):
    """Event for full agent pipeline tracking (used in Celery/Redis queues and DB)."""
    event_id: str
    timestamp: datetime
    event_type: EventType
    agent: str
    query: str
    stage_data: Dict[str, Any] = {}
    vault_event: Optional[Dict[str, Any]] = None  # Links to VaultEvent
    status: str = "PENDING"
    drift_score: float = 0.0
    trust_score: float = 1.0


class AgentRun(BaseModel):
    """Full agent execution record for demo and observability."""
    run_id: str
    agent: str
    query: str
    start_time: datetime
    end_time: Optional[datetime] = None
    pipeline_events: List[PipelineEvent] = []
    final_verdict: Verdict = Verdict.ALLOW
    replay_timeline: Optional[str] = None
    output: Dict[str, Any] = {}


class MaliciousAction(BaseModel):
    """Demo model for WITH vs WITHOUT contrast (mutated state)."""
    approved: Dict[str, Any]
    live: Dict[str, Any]
    expected_drift: float


# Re-export for convenience
__all__ = ["PipelineEvent", "AgentRun", "MaliciousAction", "EventType", "Verdict"]
