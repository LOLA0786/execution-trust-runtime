import pytest

def test_smoke_imports():
    """Minimal smoke test for key real files."""
    from core.vault.private_vault import vault
    from core.llm.grok_client import grok_client
    from agents.base_agent import BaseAgent
    from integrations.firewalled import salesforce
    assert vault is not None
    assert grok_client is not None
    assert BaseAgent is not None
    assert salesforce is not None
    print("✅ Core imports successful (real files only - GrokClient fixed)")
    print("✅ Core imports successful (real files only - GrokClient fixed)")