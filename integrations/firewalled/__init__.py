"""
Firewalled proxies for all external services.
Every call (jira.create_issue, slack.send_message, salesforce.update, etc.) is routed exclusively through PrivateVault.firewall.execute().
No direct side effects allowed.
"""
from core.vault.private_vault import vault
from typing import Any, Dict, Callable
import functools

class FirewalledProxy:
    """Base proxy that forces all methods through PrivateVault.firewall.execute()."""
    def __init__(self, service_name: str, real_client=None):
        self.service_name = service_name
        self.real_client = real_client  # None for simulation/demo

    def __getattr__(self, name: str):
        """Intercept every method call and route through firewall."""
        def wrapper(*args, **kwargs):
            task = f"{self.service_name}.{name}"
            approved_state = {"service": self.service_name, "method": name, "args": str(args)[:100], "kwargs": str(kwargs)[:100]}
            # Force through firewall (raises on BLOCK)
            return vault.firewall_executor.execute(
                lambda: self._simulate_call(name, *args, **kwargs),
                self.service_name,
                task,
                approved_state,
                *args,
                **kwargs
            )
        return wrapper

    def _simulate_call(self, method: str, *args, **kwargs) -> Dict[str, Any]:
        """Simulated execution (real client would be called here if provided)."""
        return {
            "status": "EXECUTED_VIA_FIREWALL",
            "service": self.service_name,
            "method": method,
            "result": f"Successfully called {self.service_name}.{method} (protected by PrivateVault)",
            "firewall_enforced": True
        }

# Create proxies for all external services
jira = FirewalledProxy("jira")
slack = FirewalledProxy("slack")
salesforce = FirewalledProxy("salesforce")
email = FirewalledProxy("email")
calendar = FirewalledProxy("calendar")

__all__ = ["jira", "slack", "salesforce", "email", "calendar"]
