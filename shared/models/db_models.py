"""
shared/models/db_models.py

SQLAlchemy models for Execution Trust Runtime persistence.
Tracks agent runs, checkpoints, and events with PrivateVault Merkle references.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import enum

from core.vault.private_vault import Verdict

Base = declarative_base()


class SQLEventType(str, enum.Enum):
    INPUT = "input"
    RETRIEVAL = "retrieval"
    REFLECTION = "reflection"
    RESEARCH = "research"
    DECISION = "decision"
    APPROVAL = "approval"
    EXECUTION = "execution"
    POST_CHECKPOINT = "post_checkpoint"


class AgentRunModel(Base):
    """Persistent record of full agent pipeline runs."""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, unique=True, index=True)
    agent = Column(String, index=True)
    query = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    final_verdict = Column(SQLEnum(Verdict), default=Verdict.ALLOW)
    replay_timeline = Column(String, nullable=True)
    output = Column(JSON, nullable=True)

    events = relationship("PipelineEventModel", back_populates="run")


class PipelineEventModel(Base):
    """Individual pipeline stage events with Vault linkage."""
    __tablename__ = "pipeline_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(SQLEnum(SQLEventType))
    agent = Column(String)
    stage_data = Column(JSON)
    vault_merkle_hash = Column(String, nullable=True)
    drift_score = Column(Float, default=0.0)
    trust_score = Column(Float, default=1.0)
    status = Column(String, default="COMPLETED")

    run_id = Column(Integer, ForeignKey("agent_runs.id"))
    run = relationship("AgentRunModel", back_populates="events")


class CheckpointModel(Base):
    """PrivateVault checkpoint records (Merkle, snapshots)."""
    __tablename__ = "checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String, unique=True)
    merkle_node_hash = Column(String, index=True)
    intent_drift_score = Column(Float)
    reasoning_integrity_score = Column(Float)
    approved_state_hash = Column(String)
    live_state_hash = Column(String)
    verdict = Column(SQLEnum(Verdict))
    timestamp = Column(DateTime, default=datetime.utcnow)
    agent = Column(String)
    task = Column(String)


# For alembic/migrations (mentioned in README)
__all__ = ["Base", "AgentRunModel", "PipelineEventModel", "CheckpointModel"]
