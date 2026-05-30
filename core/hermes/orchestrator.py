"""
core/hermes/orchestrator.py

Hermes multi-agent orchestrator (from hermes-agent patterns).
Handles role-based routing, structured JSON outputs (Pydantic), handoff between agents,
and coordinates the exact pipeline: Inputs → Retrieval (LangGraph) → Memory/Reflection (gbrain) 
→ Research → Decision → Approval (PrivateVault checkpoint) → Execution → Post-checkpoint.

Non-bypassable Vault integration. Additive only.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
from datetime import datetime

from core.vault.private_vault import vault, Verdict
from services.retrieval.langgraph_router import retrieval_router
from core.memory.reflection import reflection
from core.memory.vector_memory import memory


class AgentOutput(BaseModel):
    """Structured JSON output for all Hermes handoffs and decisions."""
    agent: str
    timestamp: str
    task: str
    decision: Dict[str, Any]
    confidence: float
    vault_check: Dict[str, Any]
    next_handoff: Optional[str] = None
    risks: List[str] = []
    citations: List[str] = []


class HermesOrchestrator:
    """Multi-agent orchestrator with role-based routing and structured outputs."""
    
    def __init__(self):
        self.agents = {
            "procurement": "Enterprise Procurement Agent",
            "revenue_ops": "Revenue Operations Agent",
            "chief_of_staff": "Executive Chief of Staff Agent"
        }
        self.current_context = {}
    
    def route(self, query: str, role: str = "auto") -> str:
        """Role-based routing (procurement, revenue, executive)."""
        q = query.lower()
        if "saas" in q or "vendor" in q or "contract" in q or "cancel" in q:
            return "procurement"
        elif "salesforce" in q or "pipeline" in q or "discount" in q or "revenue" in q:
            return "revenue_ops"
        else:
            return "chief_of_staff"  # default to executive synthesis
    
    def run_pipeline(self, query: str, agent_role: str = None) -> AgentOutput:
        """Exact pipeline: Inputs → Retrieval → Memory/Reflection → Research → Decision → 
        Approval (Vault checkpoint) → Execution → Post-checkpoint.
        """
        if not agent_role:
            agent_role = self.route(query)
        agent_name = self.agents.get(agent_role, "chief_of_staff")
        
        # 1. Inputs + Retrieval (LangGraph + LlamaIndex multi-hop)
        retrieval_result = retrieval_router.run(query)
        retrieved_context = retrieval_result.get("result", "No documents retrieved")
        
        # 2. Memory/Reflection (gbrain)
        memory.store(f"Query: {query}\nContext: {retrieved_context[:200]}...", 
                    {"agent": agent_role, "stage": "input"})
        reflection_summary = reflection.reflect_on_task(
            task=query, 
            outcome="retrieved enterprise data", 
            agent_name=agent_name
        )
        hierarchical_plan = reflection.generate_hierarchical_plan(query)
        
        # 3. Research (placeholder - deep loops + citations from enterprise-deep-research)
        research_findings = {
            "summary": f"Researched {query} across CRM, Jira, contracts, Slack.",
            "citations": ["Salesforce Q3 pipeline report", "Jira ticket ENG-4452", "Contract PDF v3.2"]
        }
        
        # 4. Decision (structured reasoning)
        decision = self._make_decision(agent_role, retrieved_context, research_findings, hierarchical_plan)
        
        # 5. Approval (PrivateVault checkpoint - non-bypassable)
        approved_state = {
            "decision": decision["recommendation"],
            "confidence": decision["confidence"],
            "risks": decision.get("risks", [])
        }
        live_state = approved_state.copy()  # simulate; in prod would pull real-time
        if "block" in query.lower() or "anomaly" in query.lower():
            live_state["status"] = "mutated"  # trigger drift for demo
        
        vault_event = vault.checkpoint(
            agent=agent_name,
            task=query,
            approved_state=approved_state,
            live_state=live_state,
            intent_drift_score=0.15 if "block" in query.lower() else 0.05
        )
        
        # 6. Execution (gated by vault)
        if vault_event.verdict == Verdict.BLOCK:
            execution_result = {"status": "BLOCKED", "reason": vault_event.reason, "replay": vault.generate_replay(approved_state, live_state)}
        else:
            execution_result = self._execute_action(agent_role, decision)
        
        # 7. Post-checkpoint reflection + output
        post_reflection = reflection.reflect_on_task(
            task=f"Post-execution: {query}",
            outcome=execution_result["status"],
            agent_name=agent_name
        )
        memory.store(post_reflection, {"agent": agent_role, "stage": "post"})
        
        output = AgentOutput(
            agent=agent_name,
            timestamp=datetime.now().isoformat(),
            task=query,
            decision=decision,
            confidence=decision.get("confidence", 0.85),
            vault_check={"verdict": vault_event.verdict.value, "trust_score": round(vault_event.trust_score, 3)},
            next_handoff=None,
            risks=decision.get("risks", []),
            citations=research_findings["citations"]
        )
        
        self.current_context = output.model_dump()
        return output
    
    def _make_decision(self, role: str, context: str, research: Dict, plan: Dict) -> Dict[str, Any]:
        """Role-specific structured decision logic."""
        if role == "procurement":
            return {
                "recommendation": "Cancel Datadog SaaS subscription ($180k at 12% usage). Issue Jira termination ticket.",
                "confidence": 0.92,
                "risks": ["Contract exit fees", "Migration effort"],
                "rationale": "Low utilization + reflection on historical spend patterns."
            }
        elif role == "revenue_ops":
            return {
                "recommendation": "BLOCK discount approval (10% approved vs 70% requested). Escalate to CFO.",
                "confidence": 0.95,
                "risks": ["Revenue leakage", "Customer churn"],
                "rationale": "Anomaly detected in pipeline data. PrivateVault pre-check triggered BLOCK."
            }
        else:  # chief_of_staff
            return {
                "recommendation": "Top 5 decisions: 1. Approve procurement cancellation, 2. Block revenue discount, 3. Schedule exec sync, 4. Review Q3 pipeline, 5. Vendor audit.",
                "confidence": 0.88,
                "risks": ["Execution timing", "Stakeholder alignment"],
                "rationale": "Aggregated insights from all sources with hierarchical plan."
            }
    
    def _execute_action(self, role: str, decision: Dict) -> Dict[str, Any]:
        """Simulated execution (Jira, notifications, CRM update). Gated by vault."""
        return {
            "status": "EXECUTED",
            "action_taken": decision["recommendation"],
            "result": "Packet generated and sent. Jira ticket created. CRM updated."
        }
    
    def handoff(self, from_agent: str, to_agent: str, context: Dict[str, Any]) -> AgentOutput:
        """Multi-agent handoff with structured output."""
        query = f"Handoff from {from_agent} to {to_agent}: {context.get('summary', 'Review context')}"
        return self.run_pipeline(query, to_agent.replace("_", "_"))


# Singleton orchestrator
hermes = HermesOrchestrator()
