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

from core.hermes.orchestrator import hermes
from agents.procurement.agent import procurement_agent
from agents.revenue_ops.agent import revenue_ops_agent
from agents.chief_of_staff.agent import chief_of_staff_agent
from core.vault.private_vault import vault
from shared.schemas.event_schemas import PipelineEvent, AgentRun
from celery_app import celery_app

app = FastAPI(
    title="Execution Trust Runtime API",
    description="Triggers for 3 agents with PrivateVault checkpoints. Redis/Celery backend."
)

class AgentRequest(BaseModel):
    query: str
    async_mode: bool = True


@app.post("/agents/procurement")
async def trigger_procurement(request: AgentRequest, background_tasks: BackgroundTasks):
    """Trigger Enterprise Procurement Agent (SaaS cancellations)."""
    if request.async_mode:
        task = celery_app.send_task("agents.procurement.agent.ProcurementAgent.run", args=[request.query])
        return {"task_id": task.id, "status": "queued", "agent": "procurement"}
    result = procurement_agent.run(request.query)
    return result


@app.post("/agents/revenue")
async def trigger_revenue(request: AgentRequest, background_tasks: BackgroundTasks):
    """Trigger Revenue Operations Agent (anomaly detection + BLOCK)."""
    if request.async_mode:
        task = celery_app.send_task("agents.revenue_ops.agent.RevenueOpsAgent.run", args=[request.query])
        return {"task_id": task.id, "status": "queued", "agent": "revenue_ops"}
    result = revenue_ops_agent.run(request.query)
    return result


@app.post("/agents/chief")
async def trigger_chief(request: AgentRequest, background_tasks: BackgroundTasks):
    """Trigger Executive Chief of Staff Agent (Top 5 decisions)."""
    if request.async_mode:
        task = celery_app.send_task("agents.chief_of_staff.agent.ChiefOfStaffAgent.run", args=[request.query])
        return {"task_id": task.id, "status": "queued", "agent": "chief_of_staff"}
    result = chief_of_staff_agent.run(request.query)
    return result


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
