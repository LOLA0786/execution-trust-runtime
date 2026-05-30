"""
agents/revenue_ops/agent.py

Revenue Operations Agent.
Full pipeline: Inputs (Salesforce/CRM pipeline) → Retrieval → Memory/Reflection → Research 
→ Decision (detect discount anomalies 10% approved vs 70% requested) → Approval (PrivateVault BLOCK) 
→ Execution (escalation) → Post-checkpoint.
"""
from typing import Dict, Any
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault


class RevenueOpsAgent:
    """Revenue Operations Agent focused on anomaly detection and blocking."""
    
    def __init__(self):
        self.name = "Revenue Operations Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Review Salesforce pipeline for discount anomalies") -> Dict[str, Any]:
        """Execute full pipeline with structured Pydantic JSON output. Triggers detailed BLOCK on anomalies via Vault."""
        output = self.orchestrator.run_pipeline(query, "revenue_ops")
        
        # Post-checkpoint (forensic replay if blocked) - richer demo output
        result = output.model_dump()
        if getattr(output, 'vault_snapshot', {}).get('verdict', 'ALLOW') == "BLOCK" or "BLOCK" in str(output.vault_snapshot):
            replay = vault.generate_replay(
                {"discount_approved": 0.10, "status": "approved"},
                {"discount_requested": 0.70, "status": "mutated"}
            )
            result["replay"] = replay[:400] + "... (full timeline in vault_snapshot)"
            result["pipeline_stages"] = [s.model_dump() if hasattr(s, 'model_dump') else dict(s) for s in getattr(output, 'pipeline_stages', [])]
        return result
    
    def detect_anomaly(self) -> Dict[str, Any]:
        """Demo anomaly detection (triggers Vault BLOCK)."""
        return self.run("Analyze pipeline: 10% approved vs 70% requested discount")


revenue_ops_agent = RevenueOpsAgent()
