"""
agents/procurement/agent.py

Enterprise Procurement Agent.
Full pipeline: Inputs (contracts/Jira/spend/usage) → Retrieval (LangGraph) → Memory/Reflection (gbrain) 
→ Research → Decision (SaaS cancellations e.g. Datadog $180k @12%) → Approval (PrivateVault checkpoint) 
→ Execution (Jira ticket, notifications, termination packet) → Post-checkpoint.
"""
from typing import Dict, Any
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault, vault_checkpoint, VaultCheckpointError
from integrations.firewalled import jira  # All calls must use this firewalled proxy
    """Enterprise Procurement Agent with mandatory PrivateVault gates."""
    
    def __init__(self):
        self.name = "Enterprise Procurement Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Review SaaS contracts and recommend cancellations based on usage") -> Dict[str, Any]:
        """Execute full pipeline (uses @vault_checkpoint on cancel_saas)."""
        output = self.orchestrator.run_pipeline(query, "procurement")
        result = output.model_dump()
        try:
            # Demonstrate decorator on execution step
            cancel_result = self.cancel_saas()
            result.update({"execution": cancel_result})
        except VaultCheckpointError as e:
            result["vault_block"] = str(e)
            result["status"] = "BLOCKED"
        return result
    
    @vault_checkpoint(task_name="execute_saas_cancellation")
    def cancel_saas(self, vendor: str = "Datadog", spend: int = 180000, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Specialized action with strict capability scoping (Procurement: contracts/cancellations only).
        All side effects (Jira ticket) MUST use firewalled.jira proxy.
        """
        if not state:
            state = {"vendor": vendor, "spend": spend, "usage_pct": 12, "action": "cancel_contract"}
        # Example firewalled call (enforced by proxy)
        jira.create_issue(summary=f"Cancel {vendor} SaaS", description="Low usage termination packet")
        return {
            "recommendation": f"Cancel {vendor} SaaS subscription (${spend} at {state.get('usage_pct', 12)}% usage).",
            "jira_ticket": "ENG-4452",
            "status": "EXECUTED_VIA_FIREWALL",
            "capability": "contracts_only"
        }


procurement_agent = ProcurementAgent()
