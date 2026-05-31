# AGENTS.md

## Execution Trust Runtime - Agent Development Guide (2026 Best Practices)

This repository implements a production-grade **Execution Trust Runtime** with non-bypassable PrivateVault.ai governance for autonomous agents.

### Core Principles
- **Additive Only**: All features are feature-flagged with zero regression when disabled (`VAULT_ENABLED=false`, `PROD_MODE=false`).
- **Non-Bypassable**: Every tool call, mutation, or side-effect **MUST** route through `PrivateVault.firewall.execute()` or `@vault_checkpoint` (enforced by `integrations/firewalled/*` proxies and `FirewalledExecutor`).
- **Merkle Ledger Stability**: Chain verified from event 0 (stable `event_id="stable-event-0"`, exclude volatile fields like `timestamp` in canonical JSON).
- **Human-in-the-Loop (HITL)**: Cryptographically-bound approval (`ApprovalToken` HMAC-SHA256 + `ApprovalGate`) after `CognitionSnapshot.seal()` and before execution. Uses Redis + Postgres (`approval_requests` table).
- **Real LLM Reasoning**: Use `core.llm.grok_client.grok_client.decide(...)` or `.reason(...)` for all decision/research steps (Grok-4.20-reasoning model via official xAI API). No hardcoded decisions in prod paths.
- **Firewalled Proxies**: `integrations/firewalled/{jira,slack,salesforce}.py` — all external calls delegated through `vault.firewall_executor.execute()`.
- **Testing**: Minimum 12 real pytest tests with assertions (no print-based). Cover Merkle, trust decay, approval binding, firewall, adversarial agent cases.
- **CI**: Every push runs `pytest -v --tb=no` + Docker full_demo (assert 4/4 blocked).

### Directory Structure
```
execution-trust-runtime/
├── core/
│   ├── llm/grok_client.py          # xAI/Grok reasoning backend
│   ├── vault/private_vault.py      # CognitionSnapshot, Merkle, AIFirewall, @vault_checkpoint
│   ├── approval_gate.py            # HITL with Redis/Postgres binding
│   ├── approval_token.py
│   ├── memory/                     # Vector + reflection (gbrain-style)
│   └── hermes/orchestrator.py      # Pipeline: Retrieval → Research → Decision (Grok) → Vault → Execution
├── integrations/firewalled/        # Proxies (jira.py, slack.py, salesforce_client.py)
├── agents/
│   ├── base_agent.py
│   ├── procurement/agent.py
│   ├── revenue_ops/agent.py
│   └── chief_of_staff/agent.py
├── tests/
│   ├── test_private_vault.py
│   ├── test_firewalled_integrations.py
│   ├── test_approval_gate.py
│   └── test_agents/                # 3 agents with adversarial cases
├── AGENTS.md                       # This file
├── CONTRIBUTING.md
├── .github/workflows/ci.yml
├── pyproject.toml
└── policies/default/config.yaml    # Hot-reloaded per-tenant (max_discount_pct, approvers)
```

### Coding Conventions
- **Imports**: Prefer `from core import grok_client`, `from integrations.firewalled import salesforce`.
- **LLM Usage**: In decision phase: `decision = grok_client.decide(scenario, state, model="grok-4.20-reasoning")`. Log full `reasoning`.
- **Vault**: Always decorate critical methods with `@vault_checkpoint(requires_human_approval=...)`. Use `salesforce.query(...)` (proxied).
- **Tests**: Use `pytest`, real assertions, `fakeredis`, in-memory SQLite. Parametrize adversarial cases. Run `pytest -v --tb=no`.
- **No Stubs/TODOs**: All functions fully implemented. Use existing stack only (no new deps beyond pyproject.toml).
- **Commit Messages**: `feat: add grok_client.py`, `fix: stabilize Merkle from event 0`, `test: add 12+ pytest assertions`.
- **Docs**: Keep README professional. Badge: `4/4 Scenarios Blocked ✅`. No demo polishing.

### Agent Implementation Checklist
1. Import `from core import grok_client, vault` and firewalled proxies.
2. Use Grok in `_make_decision` or `run()` for real reasoning output in logs.
3. All side-effects via `jira.`, `slack.`, `salesforce.` (enforces firewall).
4. Add adversarial test in `tests/test_agents/<role>_test.py`.
5. Update `tests/demo/full_demo.py` to call Grok during decision phase.

Follow 2026 OSS best practices: stable CI, comprehensive tests, clear contribution guidelines, production security (firewall + Merkle + HITL).

See CONTRIBUTING.md for PR process.
