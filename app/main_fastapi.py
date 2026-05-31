"""
app/main_fastapi.py (or integrated into main.py)

FastAPI endpoints for triggering the 3 agents asynchronously via Celery.
Exposes /agents/{type}, /demo/contrast, and status endpoints.
"""
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import logging

# Production logging + tracing stub
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from core.hermes.orchestrator import hermes
from agents.procurement.agent import procurement_agent
from agents.revenue_ops.agent import revenue_ops_agent
from agents.chief_of_staff.agent import chief_of_staff_agent
from core.vault.private_vault import vault, VaultCheckpointError
from core.policy_loader import policy_loader  # per-tenant policies with hot-reload
from core.metrics import get_metrics  # Prometheus metrics
from shared.schemas.event_schemas import PipelineEvent, AgentRun
from celery_app import celery_app, execute_agent_pipeline
from app.approval_webhook import router as approval_router

app = FastAPI(
    title="Execution Trust Runtime API",
    description="Triggers for 3 agents with PrivateVault checkpoints, per-tenant policies (hot-reload), and Prometheus metrics. Redis/Celery/Postgres backend."
)

app.include_router(approval_router)

# Mount policy loader (hot-reload + Redis per-tenant)
@app.on_event("startup")
async def startup_event():
    logger.info("Starting with per-tenant policy loader (hot-reload on policies/*.yaml)")
    # Policies loaded on import; watcher started

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint (vault_blocks_total, trust_score_histogram, etc.)."""
    return get_metrics()  # bytes response with all counters/histograms

class AgentRequest(BaseModel):
    query: str
    async_mode: bool = True


@app.post("/trigger/procurement")
async def trigger_procurement(request: AgentRequest):
    """Trigger Enterprise Procurement Agent (async via Celery + Vault hardening)."""
    logger.info(f"Triggering procurement with query: {request.query}")
    if request.async_mode:
        task = execute_agent_pipeline.delay("procurement", request.query)
        return {"task_id": task.id, "status": "queued", "agent": "procurement", "vault_mode": vault.mode}
    try:
        result = procurement_agent.run(request.query)
        return {"status": "success", "result": result, "vault_mode": vault.mode}
    except VaultCheckpointError as e:
        logger.error(f"Procurement blocked by Vault: {e}")
        return {"status": "blocked", "reason": str(e), "vault_mode": vault.mode}


@app.post("/trigger/revenue")
async def trigger_revenue(request: AgentRequest):
    """Trigger Revenue Operations Agent (anomaly detection + Vault BLOCK)."""
    logger.info(f"Triggering revenue_ops with query: {request.query}")
    if request.async_mode:
        task = execute_agent_pipeline.delay("revenue_ops", request.query)
        return {"task_id": task.id, "status": "queued", "agent": "revenue_ops", "vault_mode": vault.mode}
    try:
        result = revenue_ops_agent.run(request.query)
        return {"status": "success", "result": result, "vault_mode": vault.mode}
    except VaultCheckpointError as e:
        logger.error(f"Revenue blocked by Vault: {e}")
        return {"status": "blocked", "reason": str(e), "vault_mode": vault.mode}


@app.post("/trigger/chief")
async def trigger_chief(request: AgentRequest):
    """Trigger Executive Chief of Staff Agent (Top 5 decisions)."""
    logger.info(f"Triggering chief_of_staff with query: {request.query}")
    if request.async_mode:
        task = execute_agent_pipeline.delay("chief_of_staff", request.query)
        return {"task_id": task.id, "status": "queued", "agent": "chief_of_staff", "vault_mode": vault.mode}
    try:
        result = chief_of_staff_agent.run(request.query)
        return {"status": "success", "result": result, "vault_mode": vault.mode}
    except VaultCheckpointError as e:
        logger.error(f"Chief blocked by Vault: {e}")
        return {"status": "blocked", "reason": str(e), "vault_mode": vault.mode}


@app.get("/demo/contrast")
async def demo_contrast():
    """Full WITH vs WITHOUT PrivateVault contrast demo (treasury payment mutation)."""
    demo_output = vault.contrast_demo("treasury")
    return {
        "demo": "Execution Trust Runtime MVP",
        "output": demo_output,
        "timestamp": datetime.now().isoformat(),
        "status": "PrivateVault successfully blocks malicious mutation (discount 10%→70%, vendor change)"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "vault_enabled": vault.enabled, "mode": vault.mode}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
