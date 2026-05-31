"""
core/metrics.py
Prometheus metrics for Execution Trust Runtime.
Exposes /metrics endpoint with:
- vault_blocks_total (counter)
- vault_approvals_total (counter)
- trust_score_histogram (histogram)
- agent_latency_seconds (histogram)
- approval_wait_seconds (histogram)
Instrumented in vault_checkpoint, ApprovalGate, etc.
"""
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time
import logging

logger = logging.getLogger(__name__)

# Define metrics (global registry)
VAULT_BLOCKS_TOTAL = Counter(
    'vault_blocks_total', 
    'Total number of blocks by PrivateVault (firewall + approval + merkle)'
)

VAULT_APPROVALS_TOTAL = Counter(
    'vault_approvals_total',
    'Total number of human approvals processed (approved/rejected)'
)

TRUST_SCORE_HISTOGRAM = Histogram(
    'trust_score_histogram', 
    'Distribution of trust scores after checkpoint',
    buckets=[0.0, 0.1, 0.3, 0.5, 0.7, 0.85, 0.95, 1.0]
)

AGENT_LATENCY_SECONDS = Histogram(
    'agent_latency_seconds',
    'Agent execution latency in seconds (per agent/role)',
    ['agent']
)

APPROVAL_WAIT_SECONDS = Histogram(
    'approval_wait_seconds',
    'Time spent waiting for human approval (seconds)',
    buckets=[5, 30, 60, 300, 600, 1800, 3600]
)

def record_vault_block(reason: str = "unknown"):
    """Record a vault block event."""
    VAULT_BLOCKS_TOTAL.inc()
    logger.info(f"Metrics: vault_blocks_total +1 (reason={reason})")

def record_approval(decision: str = "approved"):
    """Record human approval event."""
    VAULT_APPROVALS_TOTAL.inc()
    logger.info(f"Metrics: vault_approvals_total +1 (decision={decision})")

def observe_trust_score(score: float):
    """Record trust score in histogram."""
    TRUST_SCORE_HISTOGRAM.observe(max(0.0, min(1.0, score)))

def observe_agent_latency(agent: str, latency_seconds: float):
    """Record agent execution latency."""
    AGENT_LATENCY_SECONDS.labels(agent=agent).observe(latency_seconds)

def observe_approval_wait(wait_seconds: float):
    """Record time waiting for approval."""
    APPROVAL_WAIT_SECONDS.observe(wait_seconds)

def get_metrics() -> bytes:
    """Return Prometheus metrics in text format for /metrics endpoint."""
    return generate_latest(REGISTRY)
