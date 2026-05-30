"""
agents/revenue_ops/agent.py

Revenue Operations Agent.
Full pipeline: Inputs (Salesforce/CRM pipeline) → Retrieval → Memory/Reflection → Research 
→ Decision (detect discount anomalies 10% approved vs 70% requested) → Approval (PrivateVault BLOCK) 
→ Execution (escalation) → Post-checkpoint.
"""
from typing import Dict, Any
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault, vault_checkpoint, VaultCheckpointError


class RevenueOpsAgent:
    """Revenue Operations Agent focused on anomaly detection and blocking."""
    
    def __init__(self):
        self.name = "Revenue Operations Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Review Salesforce pipeline for discount anomalies") -> Dict[str, Any]:
        """Execute full pipeline. Uses @vault_checkpoint (now routes through FirewalledExecutor.execute() for anomaly block)."""
        output = self.orchestrator.run_pipeline(query, "revenue_ops")
        result = output.model_dump() if hasattr(output, 'model_dump') else dict(output) if output else {}
        # Demonstrate firewalled decorator (graceful BLOCK for anomaly)
        try:
            anomaly_result = self.detect_anomaly(state={"pipeline": "Q3", "requested_discount": 0.70, "approved_discount": 0.10})
            result.update(anomaly_result)
        except Exception as e:  # Graceful catch for VaultCheckpointError from firewall
            result["vault_block"] = str(e)[:200]
            result["status"] = "BLOCKED"
            result["trust_score"] = 0.01
            result["replay"] = "Full pipeline trace + Merkle breach (graceful Revenue Ops handling)"
        return result

    
    @vault_checkpoint(task_name="detect_revenue_anomaly", anomaly_threshold=1)
    def detect_anomaly(self, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Graceful anomaly detection. Now uses FirewalledExecutor (firewall + capability scoping for discounts only).
        On BLOCK: returns graceful dict with replay + trust=0.01 instead of raw exception.
        """
        if not state:
            state = {"pipeline": "Q3", "requested_discount": 0.70, "approved_discount": 0.10}
        # This only executes on ALLOW; decorator handles BLOCK gracefully for Revenue Ops
        return {
            "recommendation": "BLOCK discount approval (10% approved vs 70% requested). Escalate to CFO.",
            "status": "BLOCKED_BY_VAULT",
            "anomaly_detected": True,
            "trust_score": 0.85  # only if ALLOW
        }


revenue_ops_agent = RevenueOpsAgent()
