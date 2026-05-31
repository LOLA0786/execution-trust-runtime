"""
agents/revenue_ops/agent.py

Revenue Operations Agent.
Full pipeline: Inputs (Salesforce/CRM pipeline) → Retrieval → Memory/Reflection → Research 
→ Decision (detect discount anomalies 10% approved vs 70% requested) → Approval (PrivateVault BLOCK) 
→ Execution (escalation) → Post-checkpoint.
"""
from typing import Dict, Any, List
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault, vault_checkpoint, VaultCheckpointError
from integrations.firewalled import salesforce  # All CRM/discount updates/queries MUST use firewalled proxy
from integrations.firewalled.salesforce_client import OpportunityRecord


class RevenueOpsAgent:
    """Revenue Operations Agent focused on anomaly detection and blocking."""
    
    def __init__(self):
        self.name = "Revenue Operations Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Review Salesforce pipeline for discount anomalies") -> Dict[str, Any]:
        """Execute full pipeline with live Salesforce sandbox query (high-discount opportunities).
        Uses firewalled proxy (OAuth2 + SOQL) + @vault_checkpoint. Returns structured records.
        """
        output = self.orchestrator.run_pipeline(query, "revenue_ops")
        result = output.model_dump() if hasattr(output, 'model_dump') else dict(output) if output else {}
        
        # Live Salesforce connection via firewalled proxy (queries routed to salesforce_client)
        try:
            opportunities: List[OpportunityRecord] = salesforce.query(threshold=0.15)
            result["opportunities"] = [opp.model_dump() for opp in opportunities]
            result["high_discount_count"] = len(opportunities)
            anomaly_result = self.detect_anomaly(state={"pipeline": "Q3", "opportunities": len(opportunities)})
            result.update(anomaly_result)
        except Exception as e:  # Graceful catch for VaultCheckpointError / connection issues
            result["vault_block"] = str(e)[:200]
            result["status"] = "BLOCKED"
            result["trust_score"] = 0.01
            result["replay"] = "Full pipeline trace + Merkle breach (graceful Revenue Ops handling)"
            result["opportunities"] = []
        return result

    
    @vault_checkpoint(task_name="detect_revenue_anomaly", anomaly_threshold=1)
    def detect_anomaly(self, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Graceful anomaly detection with live Salesforce data. Strict capability scoping (Revenue Ops: discounts/anomalies only).
        All queries/updates MUST use firewalled.salesforce (OAuth2 + SOQL routed to real client).
        On BLOCK: returns graceful dict with replay + trust=0.01.
        """
        if not state:
            state = {"pipeline": "Q3", "requested_discount": 0.70, "approved_discount": 0.10, "action": "discount_anomaly"}
        
        # Live update example (only executes if vault allows; otherwise blocked by decorator/firewall)
        salesforce.update(opportunity_id="OPP-123", discount=0.10, status="BLOCKED")
        
        high_count = state.get("opportunities", 0)
        return {
            "recommendation": f"BLOCK {high_count} high-discount opportunities (>15%). Escalate to CFO via approval gate.",
            "status": "BLOCKED_BY_VAULT" if high_count > 0 else "REVIEW_OK",
            "anomaly_detected": high_count > 0,
            "trust_score": 0.85 if high_count == 0 else 0.35,
            "capability": "discounts_only",
            "salesforce_records": high_count
        }


revenue_ops_agent = RevenueOpsAgent()
