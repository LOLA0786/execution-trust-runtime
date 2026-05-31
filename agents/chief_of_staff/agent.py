"""
agents/chief_of_staff/agent.py

Executive Chief of Staff Agent.
Full pipeline: Inputs (Slack/Email/Jira/CRM/Calendar) → Retrieval → Memory/Reflection 
→ Research → Decision (Top 5 decisions + risks) → Approval (PrivateVault) 
→ Execution (follow-ups, packets) → Post-checkpoint.
"""
from typing import Dict, Any, List
from core.hermes.orchestrator import hermes
from core.vault.private_vault import vault, vault_checkpoint, VaultCheckpointError
from integrations.firewalled import slack, email, calendar  # All Slack reads/posts, notifications, packets, meetings MUST use firewalled proxies


class ChiefOfStaffAgent:
    """Executive Chief of Staff Agent for synthesis and top decisions."""
    
    def __init__(self):
        self.name = "Executive Chief of Staff Agent"
        self.orchestrator = hermes
    
    def run(self, query: str = "Read recent Slack messages and surface top executive decisions") -> Dict[str, Any]:
        """Execute full pipeline with live Slack read (last 24h, channels:history). 
        Surfaces top 3 decision items, posts summary to #executive-briefing (chat:write).
        Uses firewalled proxy + @vault_checkpoint.
        """
        output = self.orchestrator.run_pipeline(query, "chief_of_staff")
        result = output.model_dump() if hasattr(output, 'model_dump') else dict(output)
        
        try:
            # Live Slack read (last 24h messages across monitored channels)
            messages = slack.read_slack_channels(last_hours=24)
            decisions_result = self.top_decisions(state={"slack_messages": messages})
            result.update({"execution": decisions_result, "slack_messages_read": len(messages)})
        except VaultCheckpointError as e:
            result["vault_block"] = str(e)
            result["status"] = "BLOCKED"
        except Exception as e:
            result["error"] = str(e)
            result["slack_status"] = "fallback_mock"
        return result

    
    @vault_checkpoint(task_name="execute_top_decisions")
    def top_decisions(self, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Live Slack analysis (last 24h messages) → surface top 3 decision items (heuristic: keywords like 'decision', 'approve', 'block', 'escalate').
        Posts structured summary to #executive-briefing. Strict capability scoping.
        All Slack calls use firewalled proxy (channels:history + chat:write scopes enforced).
        """
        messages = state.get("slack_messages", []) if state else []
        
        # Simple heuristic to surface top 3 decision-like items (production could use LLM summarization)
        decision_keywords = ["decision", "approve", "block", "escalate", "approve", "risk", "exec", "brief", "q3", "budget"]
        scored = []
        for msg in messages:
            text = msg.get("text", "").lower()
            score = sum(1 for kw in decision_keywords if kw in text)
            if score > 0:
                scored.append((score, msg))
        scored.sort(reverse=True)
        top_decisions = [msg for _, msg in scored[:3]]
        
        summary = f"""Chief of Staff Executive Briefing ({len(messages)} messages scanned, last 24h)

**Top 3 Decision Items:**
1. {top_decisions[0].get('text', 'No decisions found')[:120]}... (from {top_decisions[0].get('channel', 'unknown')})
2. {top_decisions[1].get('text', 'N/A')[:100]}... 
3. {top_decisions[2].get('text', 'N/A')[:100]}...

**Recommendation:** Review in #executive-briefing. Schedule sync if >2 high-risk items.
"""
        
        # Post summary via firewalled proxy (chat:write)
        slack.post_summary_to_channel(channel="#executive-briefing", summary=summary)
        
        # Other firewalled side effects (as before)
        email.send(to="cfo@company.com", subject="Revenue Anomaly Alert")
        calendar.create_event(title="Exec Sync", time="2026-06-01")
        
        return {
            "top_decisions": [d.get("text", "")[:80] for d in top_decisions],
            "summary_posted": True,
            "channel": "#executive-briefing",
            "messages_analyzed": len(messages),
            "status": "EXECUTED_VIA_FIREWALL",
            "capability": "notifications_packets_meetings_only",
            "vault_enforced": True
        }


chief_of_staff_agent = ChiefOfStaffAgent()
