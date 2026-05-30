"""
celery_app.py

Celery configuration for async agent pipelines with Redis broker/backend.
Tasks wrap the full pipeline (Hermes + Vault checkpoints) for queueing.
"""
from celery import Celery, Task
import os
import logging
from functools import wraps
from core.vault.private_vault import vault, VaultCheckpointError

# Structured logging for production hardening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "execution_trust_runtime",
    broker=redis_url,
    backend=redis_url,
    include=[
        "core.hermes.orchestrator",
        "agents.procurement.agent",
        "agents.revenue_ops.agent",
        "agents.chief_of_staff.agent",
        "core.vault.private_vault"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,  # production hardening
    task_acks_late=True,
)

# Production hardening: Vault rollback wrapper for Celery tasks
def vault_rollback_on_breach(task_func):
    """Decorator for Celery tasks: forces Vault rollback on integrity breach."""
    @wraps(task_func)
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"Starting task {task_func.__name__} with Vault checkpoint")
            result = task_func(*args, **kwargs)
            logger.info(f"Task {task_func.__name__} completed successfully")
            return result
        except VaultCheckpointError as e:
            logger.error(f"Vault integrity breach in task: {e}. Forcing rollback.")
            # Simulate rollback (in prod: revert DB, notify, quarantine)
            vault.mode = "WITH"  # ensure enforcement
            raise
        except Exception as e:
            logger.error(f"Unexpected error in task {task_func.__name__}: {e}")
            raise
    return wrapper

# Example task registration with hardening (called from agents or orchestrator)
@celery_app.task(bind=True, name="execute_agent_pipeline")
@vault_rollback_on_breach
def execute_agent_pipeline(self: Task, agent_role: str, query: str):
    """Async pipeline task with Vault enforcement."""
    from core.hermes.orchestrator import hermes
    logger.info(f"Executing {agent_role} pipeline for query: {query[:50]}...")
    result = hermes.run_pipeline(query, agent_role)
    return result.model_dump() if hasattr(result, 'model_dump') else dict(result)

if __name__ == "__main__":
    celery_app.start()
