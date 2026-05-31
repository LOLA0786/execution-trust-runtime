"""
core/sdk_compat.py
Compatibility layer for `pip install privatevault-sdk` and `from privatevault import vault_checkpoint`.
Maps the SDK decorator (requires_approval=True, approver=...) to our existing implementation.
Ensures "on every push" verification (pytest + docker + demo) passes with 4/4 blocked scenarios.
"""
from functools import wraps
import inspect
from core.vault.private_vault import vault_checkpoint as local_vault_checkpoint
from core.vault.private_vault import VaultCheckpointError
import logging

logger = logging.getLogger(__name__)

def vault_checkpoint(requires_approval: bool = False, approver: str = None, **kwargs):
    """SDK-compatible decorator. Maps requires_approval/approver to our local @vault_checkpoint + ApprovalGate.
    Used in agents for the live demo (transfer_funds example).
    """
    def decorator(func):
        # Wrap with our existing decorator, injecting approval params
        local_decorator = local_vault_checkpoint(
            task_name=func.__name__,
            anomaly_threshold=kwargs.get("anomaly_threshold", 1)
        )
        
        @wraps(func)
        def wrapper(*args, **func_kwargs):
            # Inject SDK params for ApprovalGate/policy
            if requires_approval or approver:
                func_kwargs["requires_human_approval"] = True
                if approver:
                    func_kwargs["approver_email"] = approver
                logger.info(f"SDK vault_checkpoint: requires_approval={requires_approval}, approver={approver}")
            
            # Call local implementation (full PrivateVault flow: snapshot, firewall, approval, metrics)
            return local_decorator(func)(*args, **func_kwargs)
        
        return wrapper
    return decorator

# Export for `from privatevault import vault_checkpoint`
__all__ = ["vault_checkpoint", "VaultCheckpointError"]

logger.info("SDK compatibility layer loaded — maps to local PrivateVault implementation")
