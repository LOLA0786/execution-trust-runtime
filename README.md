# Execution Trust Runtime

**Runtime verification for autonomous enterprise agents.**

**WITHOUT:**
AI silently executes mutated actions (Vendor_A → Offshore_Account_X, 10% → 70% discount, staging → production).

Logs show "success".

**WITH Execution Trust Runtime:**
- World-state integrity detects drift.
- Deterministic replay reconstructs exact causality (T+00s approval → T+05s mutation → T+12s breach).
- Execution BLOCKED before irreversible action.

**The contrast is the product.**

Traditional observability logs compromised execution perfectly. Execution Trust Runtime verifies the predicted world-state before execution.

## 3 Production Agents (with PrivateVault checkpoints)

### 1. Enterprise Procurement Agent
- Reads contracts, Jira, support tickets, spend, usage.
- Detects SaaS vendors to cut (e.g. Datadog $180k at 12% usage).
- Recommendation → Human approval → Hermes (Jira, notifications, termination packet).
- **PrivateVault**: Pre-read, pre-decision, post-execution checkpoints (Merkle, replay, trust decay).

### 2. Revenue Operations Agent
- Reads Salesforce, emails, CRM.
- Finds anomalies (10% approved → 70% requested).
- **BLOCK** at runtime.
- **PrivateVault**: Pre-anomaly-scan, pre-block, post-execution.

### 3. Executive Chief of Staff Agent
- Reads Slack, Email, Jira, CRM, Calendar.
- Produces Top 5 decisions + risks (revenue, escalation, vendor, hiring, security).
- Executes follow-ups (packets, meetings, notifications).
- **PrivateVault**: Pre-synthesis, pre-recommendation, post-action.

## Architecture (Production-Grade)

- **services/retrieval**: LangGraph + LlamaIndex multi-hop tool routing (from production-agentic-rag-course).
- **services/research**: Deep research loops + citation grounding (enterprise-deep-research).
- **core/memory**: Vector store, reflection loops, hierarchical planning (gbrain).
- **core/vault**: Full PrivateVault (CognitionSnapshot, Merkle chaining, forensic replay, trust decay, WITH/WITHOUT demos).
- **core/hermes**: Multi-agent handoff + structured JSON outputs + safety (hermes-agent).
- **Integrations**: Redis, Neo4j (knowledge graph), Celery queues, FastAPI endpoints.
- **tests/demo/**: Sample executions for all 3 agents with PrivateVault checkpoints.

All layers additive. Feature-flagged. Zero regression when disabled.

## Quickstart
```bash
pip install -e .
docker compose up -d
python -m alembic upgrade head
python main.py
```

See `demos/` for contrast and `scripts/validate_demos.py` for safety runner.

**This is not another agent framework.**

This is **runtime verification for autonomous execution** — the moat that makes agents enterprise-safe.
