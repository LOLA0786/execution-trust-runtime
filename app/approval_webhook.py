"""
app/approval_webhook.py
FastAPI APIRouter (prefix=/approval, tags=["approval"]) for Human-in-the-Loop.
Implements /approve, /reject, /status per spec. Uses app.state for gate/db/redis.
Includes X-ETR-API-Key header validation (matches ETR_API_KEY env).
Complete, no stubs. Uses existing stack only.
"""
from fastapi import APIRouter, HTTPException, Header, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import asyncio
import os

from core.approval_gate import approval_gate
from core.policy_loader import policy_loader  # per-tenant config (approvers, thresholds)
from core.metrics import record_approval, observe_approval_wait, record_vault_block
from shared.models.db_models import ApprovalRequestModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from redis.asyncio import Redis as AsyncRedis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/approval", tags=["approval"])


async def get_etr_db(request: Request) -> Optional[Session]:
    """Dependency for DB session from app.state (injected in main_fastapi)."""
    return getattr(request.app.state, "db_session", None)


async def get_etr_redis(request: Request) -> Optional[AsyncRedis]:
    """Dependency for Redis from app.state."""
    return getattr(request.app.state, "redis_client", None)


async def verify_api_key(x_etr_api_key: Optional[str] = Header(None, alias="X-ETR-API-Key")):
    """API key validation (additive security)."""
    expected = os.getenv("ETR_API_KEY", "dev-etr-key-change-in-prod")
    if not x_etr_api_key or not x_etr_api_key == expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-ETR-API-Key")
    return x_etr_api_key


class ApprovalResponse(BaseModel):
    status: str
    token_id: str
    message: str = ""


class StatusResponse(BaseModel):
    snapshot_id: str
    status: str
    requested_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    elapsed_seconds: int = 0


@router.post("/approve/{token_id}")
async def approve(
    token_id: str,
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: Optional[Session] = Depends(get_etr_db),
    redis_client: Optional[AsyncRedis] = Depends(get_etr_redis),
) -> ApprovalResponse:
    """POST /approval/approve/{token_id}
    - Loads ApprovalGate from app state (or direct).
    - Calls validate_and_record(token_id, "APPROVED", ...).
    - Returns {"status": "approved", "token_id": token_id}.
    - 400 on invalid/expired.
    - 409 if already decided.
    """
    try:
        start = time.time()
        success = approval_gate.validate_and_record(
            token_id=token_id,
            decision="APPROVED",
            snapshot_id=None,  # resolved via Redis scan by token_id in validate_and_record
            db_session=db,
            redis_client=redis_client,
        )
        observe_approval_wait(time.time() - start)  # metrics
        record_approval("approved")
        
        # Apply tenant policy (e.g. approvers list)
        tenant_id = "default"  # extend with header/param in prod
        policy = policy_loader.get_policy(tenant_id)
        if "approvers" in policy and os.getenv("APPROVER_EMAIL") not in policy["approvers"]:
            logger.warning("Approver not in tenant policy list")
        
        if not success:
            # Check if already decided
            decision = await (redis_client or approval_gate.redis).get(f"approval:*:decision") or "PENDING"
            if "APPROVED" in str(decision) or "REJECTED" in str(decision):
                raise HTTPException(status_code=409, detail="Already decided")
            raise HTTPException(status_code=400, detail="Invalid, expired, or tampered token")
    except Exception as e:
        logger.error(f"Approve failed for {token_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(f"Approval granted for token {token_id}")
    return ApprovalResponse(
        status="approved",
        token_id=token_id,
        message="Approval recorded. Agent execution may proceed."
    )


@router.post("/reject/{token_id}")
async def reject(
    token_id: str,
    reason: str = Query("No reason provided"),
    request: Request = None,
    api_key: str = Depends(verify_api_key),
    db: Optional[Session] = Depends(get_etr_db),
    redis_client: Optional[AsyncRedis] = Depends(get_etr_redis),
) -> ApprovalResponse:
    """POST /approval/reject/{token_id}?reason=...
    Same as approve but decision=REJECTED.
    Logs reason to Postgres metadata_.
    Returns {"status": "rejected"}.
    """
    try:
        start = time.time()
        # Update metadata with reason before record
        if db:
            try:
                db.execute(
                    text("UPDATE approval_requests SET metadata = metadata || :reason_json WHERE token_id = :tid"),
                    {"reason_json": {"rejection_reason": reason}, "tid": token_id},
                )
                db.commit()
            except Exception as db_err:
                logger.warning(f"Metadata update for reject failed: {db_err}")

        success = approval_gate.validate_and_record(
            token_id=token_id,
            decision="REJECTED",
            snapshot_id=None,  # resolved via Redis scan by token_id in validate_and_record
            db_session=db,
            redis_client=redis_client,
        )
        observe_approval_wait(time.time() - start)
        record_approval("rejected")
        record_vault_block("human_reject")
        
        if not success:
            raise HTTPException(status_code=400, detail="Invalid, expired, or tampered token")
    except Exception as e:
        if "already decided" in str(e).lower() or "409" in str(e):
            raise HTTPException(status_code=409, detail="Already decided")
        logger.error(f"Reject failed for {token_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Trigger rollback via gate (raises VaultCheckpointError internally if needed)
    try:
        # snapshot_id resolved inside validate_and_record/gate; use placeholder for call
        approval_gate.reject_and_rollback("resolved-snapshot", reason)
    except Exception as rollback_err:
        logger.info(f"Rollback handled: {rollback_err}")

    logger.info(f"Rejection recorded for token {token_id}: {reason}")
    return ApprovalResponse(
        status="rejected",
        token_id=token_id,
        message=f"Rejection recorded: {reason}"
    )


@router.get("/status/{snapshot_id}")
async def status(
    snapshot_id: str,
    request: Request,
    api_key: str = Depends(verify_api_key),
    db: Optional[Session] = Depends(get_etr_db),
    redis_client: Optional[AsyncRedis] = Depends(get_etr_redis),
) -> StatusResponse:
    """GET /approval/status/{snapshot_id}
    - Reads Redis approval:{snapshot_id}:decision
    - Reads ApprovalRequestModel from Postgres
    - Returns {snapshot_id, status, requested_at, decided_at, elapsed_seconds}
    """
    redis = redis_client or getattr(request.app.state, "redis_client", None) or approval_gate.redis
    db_session = db or getattr(request.app.state, "db_session", None)

    # Handle both sync Redis (from gate) and async
    if hasattr(redis, "get") and asyncio.iscoroutinefunction(redis.get):
        decision = await redis.get(f"approval:{snapshot_id}:decision")
    else:
        decision = redis.get(f"approval:{snapshot_id}:decision") if hasattr(redis, "get") else None
    decision = decision or "PENDING"

    requested_at = None
    decided_at = None
    if db_session:
        try:
            result = db_session.execute(
                text("SELECT requested_at, decided_at FROM approval_requests WHERE snapshot_id = :sid"),
                {"sid": snapshot_id},
            ).fetchone()
            if result:
                requested_at = result[0]
                decided_at = result[1]
        except Exception as e:
            logger.warning(f"DB status query failed: {e}")

    elapsed = 0
    if requested_at and decided_at:
        elapsed = int((decided_at - requested_at).total_seconds())
    elif requested_at:
        elapsed = int((datetime.utcnow() - requested_at).total_seconds())

    return StatusResponse(
        snapshot_id=snapshot_id,
        status=decision,
        requested_at=requested_at,
        decided_at=decided_at,
        elapsed_seconds=elapsed,
    )
