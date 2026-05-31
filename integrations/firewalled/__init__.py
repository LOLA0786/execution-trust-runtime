"""
Firewalled proxies for all external services.
Every call (jira.create_issue, slack.send_message, salesforce.update, etc.) is routed exclusively through PrivateVault.firewall.execute().
No direct side effects allowed.
"""
from core.vault.private_vault import vault
from typing import Any, Dict, Callable, List
import functools
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Import real clients for live services
from .salesforce_client import salesforce_client
from services.notifier import notifier  # for live Slack read/post (Chief of Staff)

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

    def _simulate_call(self, method: str, *args, **kwargs) -> Any:
        """Delegate to real_client (Salesforce) or notifier.slack (for Chief of Staff Slack read/post).
        Preserves full PrivateVault enforcement (firewall, checkpoint, approval, Merkle ledger).
        Supports new methods: read_slack_channels, post_summary_to_channel.
        """
        if self.service_name == "slack" and method in ("read_slack_channels", "send_message", "post_summary_to_channel"):
            # Route Chief of Staff Slack ops through real notifier (scopes: channels:history, chat:write)
            try:
                if method == "read_slack_channels":
                    last_hours = kwargs.get("last_hours", 24)
                    return notifier.read_slack_channels(last_hours=last_hours)
                elif method == "post_summary_to_channel" or method == "send_message":
                    channel = kwargs.get("channel", "#executive-briefing")
                    summary = kwargs.get("summary") or kwargs.get("message", "Chief of Staff summary posted via firewall.")
                    return notifier.post_to_channel(channel=channel, summary=summary)
            except Exception as e:
                logger.warning(f"Slack delegation failed: {e}")
        
        if self.real_client and hasattr(self.real_client, method):
            # Live Salesforce (or other real clients)
            try:
                if method == "query":
                    # Delegate to FirewalledSalesforceClient.query (SOQL or mock with 70% discount for demo)
                    soql = args[0] if args else "SELECT ... FROM Opportunity"
                    return self.real_client.query(soql)
                if method == "update_opportunity":
                    opp_id = args[0] if args else ""
                    fields = args[1] if len(args) > 1 else kwargs
                    return self.real_client.update_opportunity(opp_id, fields)
                return getattr(self.real_client, method)(*args, **kwargs)
            except Exception as e:
                return {"status": "ERROR", "service": self.service_name, "error": str(e)}
        
        # Default simulation for other services/methods
        return {
            "status": "EXECUTED_VIA_FIREWALL",
            "service": self.service_name,
            "method": method,
            "result": f"Successfully called {self.service_name}.{method} (protected by PrivateVault)",
            "firewall_enforced": True
        }

# Create proxies for all external services (inject real client for Salesforce)
jira = FirewalledProxy("jira")
slack = FirewalledProxy("slack")
salesforce = FirewalledProxy("salesforce", real_client=salesforce_client)
email = FirewalledProxy("email")
calendar = FirewalledProxy("calendar")

__all__ = ["jira", "slack", "salesforce", "email", "calendar"]
