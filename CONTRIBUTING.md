# CONTRIBUTING.md

## Contributing to Execution Trust Runtime

Thank you for considering contributing to this production-grade open-source agent governance runtime.

### Code of Conduct
- Respectful, professional communication.
- Focus on code quality, stability, and real enforcement (Merkle ledger, non-bypassable firewall, HITL approval).
- Follow "additive only, feature-flagged, zero regression" rule.

### Development Setup
1. Clone the repo: `git clone https://github.com/LOLA0786/execution-trust-runtime`
2. Install: `pip install -e ".[test]"`
3. Copy `.env.example` to `.env` and fill keys (especially `XAI_API_KEY` for Grok reasoning).
4. Run tests: `pytest -v --tb=no`
5. Run demo: `python -m tests.demo.full_demo`
6. Start services: `docker compose up -d` (Postgres, Redis).

### Key Guidelines (2026 Best Practices for Agent Runtimes)
- **Architecture**: Do not redesign. All changes additive and feature-flagged (`if vault.enabled`, policy-driven).
- **Security**: Every external/integration call **must** use `integrations/firewalled/*` proxies which route exclusively through `PrivateVault.firewall.execute()`. No direct `requests`, `slack_sdk` outside notifier.
- **LLM Integration**: Use `from core.llm.grok_client import grok_client`. Call `grok_client.decide(scenario, state)` or `grok_client.reason(prompt)` in decision/research phases. Show real reasoning in logs. Support model selection (`grok-4.20-reasoning`, etc.). Key in env (`XAI_API_KEY`).
- **Testing**: Minimum 12 real `pytest` tests with assertions (no `print`). Cover:
  - `tests/test_private_vault.py`: Merkle stability (from event 0), trust decay, ApprovalBinding, firewall blocks.
  - `tests/test_firewalled_integrations.py`: Proxy enforcement for Jira/Slack/Salesforce.
  - `tests/test_agents/*.py`: Adversarial cases for all 3 agents (procurement, revenue_ops, chief_of_staff).
  - Existing: `test_approval_gate.py` (5 tests with fakeredis + SQLite).
- **Merkle Ledger**: Must remain stable from event 0. Use `stable-event-0`, exclude volatile fields (`timestamp`, `event_id`) in canonical JSON for `compute_merkle_hash` and `verify_chain`.
- **Docs**: Update AGENTS.md for any new conventions. Keep README professional with badge `4/4 Scenarios Blocked ✅`.
- **CI**: `.github/workflows/ci.yml` must pass (pytest + docker demo assert 4/4 blocked).
- **No Demo Polishing**: Focus on code quality, real tests, enforcement. No extra output formatting.

### Pull Request Process
1. Branch from `main`: `git checkout -b feature/grok-integration`.
2. Make changes (small, incremental commits with clear messages e.g. "feat: integrate grok_client as reasoning backend").
3. Run `pytest -v --tb=no` locally — all tests must pass.
4. Update relevant tests/docs.
5. Push and open PR with description referencing AGENTS.md conventions.
6. CI will run full verification (pytest, Docker, Grok-powered scenarios).

### Architecture Notes
- Core: `core/vault/private_vault.py` (CognitionSnapshot, Merkle, AIFirewall, ApprovalGate integration).
- Agents: Use Hermes orchestrator pipeline with Grok in decision phase.
- Proxies: `integrations/firewalled/` — universal enforcement.
- Tests: Real assertions, adversarial coverage.
- Deployment: Railway/Docker with public HTTPS for approval webhooks.

Questions? Open an issue or see AGENTS.md for full structure.

Last updated: 2026.
