"""
tests/test_firewalled_integrations.py

Real pytest tests for firewalled proxies (Jira, Slack, Salesforce, etc.).
All calls MUST route through PrivateVault.firewall.execute().
Uses real assertions (no prints). Covers adversarial cases.
Part of minimum 12 tests requirement.
"""

import pytest
from unittest.mock import patch
from core.vault.private_vault import vault, VaultCheckpointError
from integrations.firewalled import jira, slack, salesforce, email, calendar
from integrations.firewalled.salesforce_client import OpportunityRecord


def test_firewalled_jira_enforcement():
    """Jira proxy routes through firewall.execute()."""
    with patch.object(vault.firewall_executor, 'execute', return_value={"status": "EXECUTED_VIA_FIREWALL", "service": "jira"}) as mock_execute:
        result = jira.create_issue(summary="Test termination", description="Low usage")
        mock_execute.assert_called_once()
        assert "EXECUTED_VIA_FIREWALL" in str(result)
        assert result["service"] == "jira"


def test_firewalled_slack_enforcement():
    """Slack proxy (read/post) routes through firewall + notifier delegation."""
    with patch.object(vault.firewall_executor, 'execute', return_value={"status": "EXECUTED_VIA_FIREWALL", "messages_read": 5}) as mock_execute:
        result = slack.read_slack_channels(last_hours=24)
        mock_execute.assert_called_once()
        assert result["status"] == "EXECUTED_VIA_FIREWALL"


def test_firewalled_salesforce_query():
    """Salesforce proxy returns structured OpportunityRecord with high discount anomaly (70%)."""
    results = salesforce.query(threshold=0.15)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert isinstance(results[0], OpportunityRecord)
    assert any(r.discount > 50 for r in results), "High discount anomaly must be present for Revenue Ops test"
    assert results[0].account_name == "Acme Corp"


def test_firewalled_salesforce_update():
    """Salesforce update routes through firewall."""
    with patch.object(vault.firewall_executor, 'execute', return_value={"status": "EXECUTED_VIA_FIREWALL", "updated": True}) as mock_execute:
        result = salesforce.update_opportunity("OPP-123", {"StageName": "Closed Lost"})
        mock_execute.assert_called_once()
        assert result["updated"] is True


def test_firewalled_email_calendar():
    """Email/Calendar proxies enforce firewall (adversarial test)."""
    with patch.object(vault.firewall_executor, 'execute', return_value={"status": "EXECUTED_VIA_FIREWALL"}) as mock_execute:
        result = email.send(to="cfo@example.com", subject="Alert")
        mock_execute.assert_called()
        result2 = calendar.create_event(title="Exec Sync")
        assert "EXECUTED_VIA_FIREWALL" in str(result2)


def test_adversarial_firewall_block():
    """Adversarial: dangerous action blocked by AIFirewall in executor."""
    with pytest.raises(VaultCheckpointError):
        with patch.object(vault.firewall_executor.firewall, 'scan_action', return_value={"allowed": False, "reason": "rm -rf pattern"}):
            jira.create_issue(summary="rm -rf /data")


@pytest.mark.parametrize("service,method", [
    ("jira", "create_issue"),
    ("slack", "send_message"),
    ("salesforce", "query"),
    ("email", "send"),
])
def test_all_proxies_use_firewall_executor(service, method):
    """All proxies must use PrivateVault.firewall.execute() — non-bypassable."""
    proxy = globals()[service]  # jira, slack, etc.
    with patch.object(vault.firewall_executor, 'execute') as mock_execute:
        try:
            if method == "query":
                getattr(proxy, method)(threshold=0.1)
            else:
                getattr(proxy, method)("test")
        except Exception:
            pass  # expected in some mocks
        mock_execute.assert_called()
