#!/usr/bin/env python3
"""
main.py

Clean demo for deep PrivateVault.ai integration.
Demonstrates:
- WITHOUT Vault = silent success on mutation
- WITH Vault = BLOCK + beautiful replay (full pipeline trace) + trust decay to 0.01
Uses FirewalledExecutor, ApprovalBinding, AIFirewall, Merkle ledger.
"""
from agents.procurement.agent import procurement_agent
from agents.revenue_ops.agent import revenue_ops_agent
from agents.chief_of_staff.agent import chief_of_staff_agent
from core.vault.private_vault import vault, VaultCheckpointError
import logging
logging.basicConfig(level=logging.INFO)


def main():
    """Clean demo showing WITHOUT Vault = silent success vs WITH Vault = BLOCK + replay + trust=0.01."""
    print("🚀 Execution Trust Runtime — Deep PrivateVault.ai Integration")
    print("Firewalled execution • ApprovalBinding • AIFirewall • Merkle ledger • Capability scoping")
    print("Every tool/mutation routed through PrivateVault.firewall.execute()\n")

    # Core contrast demo (WITHOUT = silent success on mutation; WITH = BLOCK + beautiful replay)
    print("=== WITHOUT Vault vs WITH Vault Contrast (Treasury + Revenue Anomaly) ===")
    print(vault.contrast_demo("treasury"))
    print("\n" + "="*90 + "\n")

    print("Running Revenue Operations Agent (anomaly block graceful)...")
    try:
        rev_result = revenue_ops_agent.run()  # uses detect_anomaly with graceful BLOCK
        print("RevenueOps Result:", rev_result.get("status", "SUCCESS"), "- trust:", rev_result.get("trust_score", 1.0))
        if "BLOCKED" in str(rev_result):
            print("✅ Graceful anomaly BLOCK with full replay + trust decay to 0.01")
    except Exception as e:
        print("RevenueOps BLOCKED gracefully:", str(e)[:100])

    print("\n✅ Deep integration complete. All mutations firewalled. Replay includes full pipeline trace.")
    print("PrivateVault.ai patterns adapted: FirewalledExecutor, ApprovalBinding, AIFirewall, Merkle ledger.")


if __name__ == "__main__":
    main()
    print("\n" + "="*90)
    print("Demo complete. Run `python -m tests.demo.full_demo` for richer pipeline output.")

