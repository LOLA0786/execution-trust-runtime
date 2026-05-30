"""
agents/procurement/agent.py

Enterprise Procurement Agent.
Full pipeline: Inputs (contracts/Jira/spend/usage) → Retrieval (LangGraph) → Memory/Reflection (gbrain) 
→ Research → Decision (SaaS cancellations e.g. Datadog $180k @12%) → Approval (PrivateVault checkpoint) 
→ Execution (Jira ticket, notifications, termination packet) → Post-checkpoint.
"""
from typing import Dict, Any
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault


class ProcurementAgent:
    """Enterprise Procurement Agent with mandatory PrivateVault gates."""
    
    def __init__(self):
        self.name = "Enterprise Procurement Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Review SaaS contracts and recommend cancellations based on usage") -> Dict[str, Any]:
        """Execute full pipeline with non-bypassable Vault checkpoint."""
        output = self.orchestrator.run_pipeline(query, "procurement")
        
        # Post-checkpoint reflection (additive)
        if output.vault_check["verdict"] != "BLOCK":
            vault_event = vault.checkpoint(
                agent=self.name,
                task="post_execution_review",
                approved_state={"status": "executed", "recommendation": output.decision["recommendation"]},
                intent_drift_score=0.02
            )
            return output.model_dump() | {"post_vault": vault_event.verdict.value}
        return output.model_dump()
    
    def cancel_saas(self, vendor: str = "Datadog", spend: int = 180000) -> Dict[str, Any]:
        """Specialized action for SaaS optimization demo."""
        query = f"Analyze and cancel {vendor} contract at ${spend} with low usage"
        return self.run(query)


procurement_agent = ProcurementAgent()
