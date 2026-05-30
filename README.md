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

```
Execution Trust Runtime
├── FastAPI API (/trigger/*) ──→ Celery Tasks (Redis broker)
│     │
│     └─→ HermesOrchestrator (registration + handoff)
│           │
│           ├── Retrieval (LangGraph + LlamaIndex multi-hop router + fallback)
│           ├── Memory (VectorMemory/Chroma + ReflectionEngine + hierarchical plan)
│           ├── Decision (structured Pydantic)
│           ├── PrivateVault (CognitionSnapshot, @vault_checkpoint decorator,
│           │             Merkle proof, state_diff, trust_decay(time+anomalies),
│           │             forced rollback on breach, forensic replay)
│           └── Execution (gated, with Vault post-checkpoint)
│
├── Logging + Tracing (structured logs per stage, OpenTelemetry spans)
├── Error Handling (VaultCheckpointError → rollback + alert)
└── Persistence (SQLAlchemy models, Redis backend, memory_db/)
```

**Current Capabilities**:
- **Core Memory**: Persistent Chroma vector store, gbrain-style reflection loops, hierarchical task planning (Research/Analyze/Decide/Verify).
- **Retrieval**: Full LangGraph multi-hop router with LlamaIndex, tool fallback, Vault pre-gating.
- **Hermes**: Agent registration, handoff history, structured `AgentOutput` (pipeline stages + vault_snapshot).
- **PrivateVault**: `@vault_checkpoint` decorator (mandatory), enhanced `CognitionSnapshot` (before/after diff, Merkle proof), `trust_decay(time + anomaly_count)`, forced rollback on breach, deterministic replay with proof.
- **Production Hardening**: Redis + Celery async queues (with Vault wrapper), FastAPI endpoints (`/trigger/procurement`, `/trigger/revenue`, `/trigger/chief`), Docker Compose (Redis primary), structured logging/tracing, error rollback.
- **Models**: Full Pydantic (`PipelineEvent`, `AgentRun`, `VaultSnapshot`, `Decision`) + SQLAlchemy (`AgentRunModel`, `CheckpointModel`).
- **Demo**: Rich output with 3 agents, BLOCK on anomalous discount, contrast (WITH vs WITHOUT).

All additive/feature-flagged. Zero regression when `vault.enabled=False`. Traditional observability logs compromised execution; this **verifies before execution**.

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
