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
        """Execute full pipeline. Uses @vault_checkpoint on detect_anomaly for deeper enforcement."""
        output = self.orchestrator.run_pipeline(query, "revenue_ops")
        result = output.model_dump()
        # Demonstrate decorator in action via direct call (handles BLOCK via exception in real use)
        try:
            anomaly_result = self.detect_anomaly()
            result.update(anomaly_result)
        except VaultCheckpointError as e:
            result["vault_block"] = str(e)
            result["status"] = "BLOCKED"
        return result

    
    @vault_checkpoint(task_name="detect_revenue_anomaly", anomaly_threshold=1)
    def detect_anomaly(self, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Demo anomaly detection using @vault_checkpoint decorator (enforces BLOCK on discount mutation)."""
        if not state:
            state = {"pipeline": "Q3", "requested_discount": 0.70, "approved_discount": 0.10}
        # Simulated execution only reaches here on ALLOW (demo uses high drift for BLOCK)
        return {
            "recommendation": "BLOCK discount approval (10% approved vs 70% requested). Escalate to CFO.",
            "status": "BLOCKED_BY_VAULT",
            "anomaly_detected": True
        }


revenue_ops_agent = RevenueOpsAgent()
