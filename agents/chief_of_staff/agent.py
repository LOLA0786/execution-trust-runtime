"""
agents/chief_of_staff/agent.py

Executive Chief of Staff Agent.
Full pipeline: Inputs (Slack/Email/Jira/CRM/Calendar) → Retrieval → Memory/Reflection 
→ Research → Decision (Top 5 decisions + risks) → Approval (PrivateVault) 
→ Execution (follow-ups, packets) → Post-checkpoint.
"""
from typing import Dict, Any
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault, vault_checkpoint, VaultCheckpointError


class ChiefOfStaffAgent:
    """Executive Chief of Staff Agent for synthesis and top decisions."""
    
    def __init__(self):
        self.name = "Executive Chief of Staff Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Aggregate all sources and produce Top 5 decisions with risks") -> Dict[str, Any]:
        """Execute full pipeline (uses @vault_checkpoint on top_decisions for enforcement)."""
        output = self.orchestrator.run_pipeline(query, "chief_of_staff")
        result = output.model_dump()
        try:
            decisions_result = self.top_decisions()
            result.update({"execution": decisions_result})
        except VaultCheckpointError as e:
            result["vault_block"] = str(e)
            result["status"] = "BLOCKED"
        return result

    
    @vault_checkpoint(task_name="execute_top_decisions")
    def top_decisions(self, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Top decisions action using @vault_checkpoint decorator."""
        if not state:
            state = {"decisions": 5, "risks_identified": 3}
        return {
            "recommendation": "Top 5 decisions: 1. Procurement cancel, 2. Revenue BLOCK, 3. Exec sync, 4. Pipeline review, 5. Audit.",
            "risks": ["timing", "alignment", "compliance"],
            "status": "EXECUTED"
        }


chief_of_staff_agent = ChiefOfStaffAgent()
