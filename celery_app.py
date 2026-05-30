"""
celery_app.py

Celery configuration for async agent pipelines with Redis broker/backend.
Tasks wrap the full pipeline (Hermes + Vault checkpoints) for queueing.
"""
from celery import Celery
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "execution_trust_runtime",
    broker=redis_url,
    backend=redis_url,
    include=["core.hermes.orchestrator", "agents.procurement.agent", "agents.revenue_ops.agent", "agents.chief_of_staff.agent"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min timeout for full pipeline
)

# Optional: beat for scheduled demos
# from celery.schedules import crontab
# celery_app.conf.beat_schedule = { ... }

if __name__ == "__main__":
    celery_app.start()
