"""
agents/chief_of_staff/agent.py

Executive Chief of Staff Agent.
Full pipeline: Inputs (Slack/Email/Jira/CRM/Calendar) → Retrieval → Memory/Reflection 
→ Research → Decision (Top 5 decisions + risks) → Approval (PrivateVault) 
→ Execution (follow-ups, packets) → Post-checkpoint.
"""
from typing import Dict, Any
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault


class ChiefOfStaffAgent:
    """Executive Chief of Staff Agent for synthesis and top decisions."""
    
    def __init__(self):
        self.name = "Executive Chief of Staff Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Aggregate all sources and produce Top 5 decisions with risks") -> Dict[str, Any]:
        """Execute full pipeline for executive synthesis."""
        output = self.orchestrator.run_pipeline(query, "chief_of_staff")
        
        # Post-checkpoint reflection
        vault_event = vault.checkpoint(
            agent=self.name,
            task="executive_summary_review",
            approved_state={"decisions": output.decision.get("recommendation", "Top 5 listed"), "risks": output.risks},
            intent_drift_score=0.08
        )
        return output.model_dump() | {"post_vault_verdict": vault_event.verdict.value}
    
    def top_decisions(self) -> Dict[str, Any]:
        """Demo for Top 5 executive decisions."""
        return self.run("Synthesize Slack, Email, Jira, CRM, Calendar into Top 5 decisions with risks and follow-ups")


chief_of_staff_agent = ChiefOfStaffAgent()
