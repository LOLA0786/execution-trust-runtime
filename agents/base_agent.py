"""
base_agent.py

Base class for all 3 agents (Procurement, Revenue Ops, Chief of Staff).
Uses PrivateVault checkpoints at critical points.
Skeleton only — no complex logic yet.
"""
from typing import Dict, Any
from core.vault.private_vault import vault


class BaseAgent:
    """Base for Execution Trust Runtime agents. All actions gated by PrivateVault."""
    
    def __init__(self, name: str):
        self.name = name
        self.vault = vault
    
    def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """All execution paths go through PrivateVault checkpoint."""
        # Pre-checkpoint (additive)
        snapshot = {"id": "snapshot-001", "state": task.get("approved_state", {})}
        check = self.vault.validate_before_execution(snapshot, task)
        
        if check["verdict"] == "BLOCK":
            return {"status": "BLOCKED", "replay": check.get("replay", [])}
        
        # Execution would go here in full implementation
        return {"status": "EXECUTED", "result": "success"}
