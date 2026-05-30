"""
base_agent.py

Base for the 3 specialized agents. Enforces the exact pipeline with shared runtime.
All agents delegate to HermesOrchestrator for Retrieval/Memory/Reflection/Research/Decision/Vault/Execution.
"""
from typing import Dict, Any
from core.vault.private_vault import vault
from core.hermes.orchestrator import hermes


class BaseAgent:
    """Base class enforcing the full Execution Trust Runtime pipeline."""
    
    def __init__(self, name: str, role: str = "chief_of_staff"):
        self.name = name
        self.role = role
        self.vault = vault
        self.orchestrator = hermes
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Delegates to orchestrator for the full pipeline (non-bypassable Vault)."""
        query = task.get("query", str(task))
        output = self.orchestrator.run_pipeline(query, self.role)
        return output.model_dump()
