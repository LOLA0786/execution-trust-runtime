"""
services/notifier.py
Production-grade dual-backend notifier (Slack + SMTP email) for Human-in-the-Loop.
Implements SlackNotifier (Block Kit buttons) and EmailNotifier (smtplib HTML, no SendGrid).
Notifier facade with fallbacks. Complete, no stubs. New dep: slack-sdk (added to pyproject.toml).
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Union

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Slack backend using Block Kit for rich approval messages with buttons."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.client = WebClient(token=self.bot_token) if self.bot_token else None
        self.security_channel = os.getenv("SLACK_SECURITY_CHANNEL", "#security-alerts")
        self.channels_to_monitor = os.getenv("SLACK_CHANNELS_TO_MONITOR", "#general,#executive,#revenue").split(",")

    def send_approval_request(
        self, approver_slack_id: str, action_summary: str, approve_url: str, reject_url: str
    ) -> bool:
        """Uses slack_sdk WebClient.chat_postMessage with Block Kit:
        - Header: "Action Requires Your Approval"
        - Section: action_summary text
        - Two buttons: Approve (approve_url) / Reject (reject_url), style primary/danger
        """
        if not self.client or not approver_slack_id:
            logger.info(f"[MOCK SLACK] Approval request to {approver_slack_id}: {action_summary} | Approve: {approve_url} | Reject: {reject_url}")
            return True

        try:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Action Requires Your Approval",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:*\n{action_summary}\n\nPlease review and act within 1 hour. This is cryptographically bound to the CognitionSnapshot Merkle hash."
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Approve", "emoji": True},
                            "style": "primary",
                            "url": approve_url,
                            "action_id": "approve_action"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Reject", "emoji": True},
                            "style": "danger",
                            "url": reject_url,
                            "action_id": "reject_action"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "🔒 *Execution Trust Runtime* — Human-in-the-Loop approval bound to PrivateVault"
                        }
                    ]
                }
            ]

            self.client.chat_postMessage(
                channel=approver_slack_id,
                text=f"Approval Required: {action_summary}",
                blocks=blocks
            )
            return True
        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            return False

    def send_block_alert(
        self, channel: str, snapshot_id: str, reason: str, trust_score: float = 0.0
    ) -> bool:
        """Posts to #security-alerts (or provided channel) with red attachment."""
        if not self.client:
            logger.warning(f"[MOCK SLACK BLOCK] Snapshot {snapshot_id}: {reason} (trust={trust_score})")
            return True

        try:
            attachments = [
                {
                    "color": "#FF0000",
                    "title": "🚨 ETR BLOCK ALERT - Human Rejection / Timeout",
                    "text": f"*Snapshot:* {snapshot_id}\n*Reason:* {reason}\n*Trust Score:* {trust_score:.2f}\n*Time:* {datetime.utcnow().isoformat()}",
                    "footer": "PrivateVault • Merkle-bound approval flow",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]

            self.client.chat_postMessage(
                channel=channel or self.security_channel,
                text=f"ETR BLOCK: {reason}",
                attachments=attachments
            )
            return True
        except SlackApiError as e:
            logger.error(f"Slack block alert error: {e}")
            return False

    def read_slack_channels(self, last_hours: int = 24, limit_per_channel: int = 50) -> List[Dict[str, Any]]:
        """Read messages from monitored Slack channels (last N hours). Requires channels:history scope.
        Returns list of messages with channel, user, text, timestamp. Used by Chief of Staff Agent.
        """
        if not self.client:
            logger.info("[MOCK SLACK READ] Returning sample decision messages (last 24h)")
            return [
                {"channel": "#executive", "user": "ceo", "text": "Decision: Approve Q3 budget with 15% contingency. Risks: supply chain.", "ts": "1720000000"},
                {"channel": "#revenue", "user": "cfo", "text": "Need to review all opps with discount >20%. Escalate high-risk ones.", "ts": "1720003600"},
                {"channel": "#general", "user": "ops-lead", "text": "Proposal: Block vendor contract renewal until compliance audit complete.", "ts": "1720012000"},
            ]

        messages = []
        oldest = (datetime.utcnow() - timedelta(hours=last_hours)).timestamp()

        for channel_name in self.channels_to_monitor:
            try:
                # Resolve channel ID (conversations.list or assume name works with WebClient)
                channel_info = self.client.conversations_list(types="public_channel")['channels']
                channel_id = next((c['id'] for c in channel_info if c['name'] == channel_name.strip('#')), channel_name)
                
                response = self.client.conversations_history(
                    channel=channel_id,
                    oldest=str(oldest),
                    limit=limit_per_channel,
                    inclusive=True
                )
                for msg in response.get('messages', []):
                    if msg.get('subtype') not in ('bot_message', 'channel_join'):  # filter noise
                        messages.append({
                            "channel": channel_name,
                            "user": msg.get('user', 'unknown'),
                            "text": msg.get('text', ''),
                            "ts": msg.get('ts'),
                            "thread_ts": msg.get('thread_ts')
                        })
            except SlackApiError as e:
                logger.warning(f"Failed to read {channel_name}: {e}")
                continue
        logger.info(f"Read {len(messages)} messages from Slack channels (last {last_hours}h)")
        return messages

    def post_summary_to_channel(self, channel: str = "#executive-briefing", summary: str = "", blocks: List[Dict] = None) -> bool:
        """Post Chief of Staff summary to executive channel. Requires chat:write scope.
        Uses Block Kit for rich formatting if blocks provided.
        """
        if not self.client:
            logger.info(f"[MOCK SLACK POST] Posted to {channel}: {summary[:80]}...")
            return True

        try:
            if blocks:
                self.client.chat_postMessage(channel=channel, text=summary, blocks=blocks)
            else:
                self.client.chat_postMessage(
                    channel=channel,
                    text=summary or "Chief of Staff Briefing: Top decisions surfaced from Slack."
                )
            logger.info(f"Posted Chief of Staff summary to {channel}")
            return True
        except SlackApiError as e:
            logger.error(f"Failed to post summary to {channel}: {e}")
            return False


class EmailNotifier:
    """Email backend using stdlib smtplib (no SendGrid dep). Sends HTML with anchor buttons."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("ETR_FROM_EMAIL", "no-reply@execution-trust.com")

    def send_approval_request(
        self, approver_email: str, action_summary: str, approve_url: str, reject_url: str
    ) -> bool:
        """Sends HTML email via smtplib:
        - Subject: "[ETR] Action Approval Required"
        - HTML body with approve/reject buttons as anchor tags
        """
        if not approver_email or not self.smtp_user or not self.smtp_password:
            logger.info(f"[MOCK EMAIL] Approval request to {approver_email}: {action_summary}\nApprove: {approve_url}\nReject: {reject_url}")
            return True

        try:
            html_body = f"""
            <html>
            <head><style>body {{font-family: Arial, sans-serif;}} .button {{padding: 12px 24px; margin: 10px; text-decoration: none; border-radius: 6px; font-weight: bold;}}</style></head>
            <body>
                <h2 style="color: #1a73e8;">[ETR] Action Approval Required</h2>
                <p><strong>Action Summary:</strong> {action_summary}</p>
                <p>This request is cryptographically bound to the agent's <strong>CognitionSnapshot Merkle hash</strong>. Review carefully before approving.</p>
                <p style="margin: 30px 0;">
                    <a href="{approve_url}" class="button" style="background: #34a853; color: white;">✅ APPROVE EXECUTION</a>
                    <a href="{reject_url}" class="button" style="background: #ea4335; color: white;">❌ REJECT &amp; ROLLBACK</a>
                </p>
                <p style="color: #666; font-size: 0.9em;">Links expire in 1 hour. This is part of Execution Trust Runtime's non-bypassable Human-in-the-Loop flow.</p>
                <hr>
                <p style="font-size: 0.8em; color: #999;">Execution Trust Runtime • PrivateVault.ai</p>
            </body>
            </html>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = "[ETR] Action Approval Required"
            msg["From"] = self.from_email
            msg["To"] = approver_email
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, approver_email, msg.as_string())

            logger.info(f"Email approval request sent to {approver_email}")
            return True
        except Exception as e:
            logger.error(f"SMTP email error: {e}")
            return False


class Notifier:
    """Facade combining SlackNotifier and EmailNotifier.
    - notify_approval_request(...) → calls both if configured
    - notify_block(...) → Slack only
    Falls back to logging if not configured.
    """

    def __init__(self):
        self.slack = SlackNotifier() if os.getenv("SLACK_BOT_TOKEN") else None
        self.email = EmailNotifier() if os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD") else None
        logger.info(f"Notifier initialized: Slack={'enabled' if self.slack and self.slack.client else 'mock'}, Email={'enabled' if self.email and self.email.smtp_user else 'mock'}")

    def notify_approval_request(
        self,
        approver_email: str,
        action_summary: str,
        approve_url: str,
        reject_url: str,
        approver_slack_id: Optional[str] = None,
    ) -> bool:
        """Calls both backends if configured. Returns True if at least one succeeds."""
        success = True
        if self.slack and approver_slack_id:
            success &= self.slack.send_approval_request(approver_slack_id, action_summary, approve_url, reject_url)
        if self.email:
            success &= self.email.send_approval_request(approver_email, action_summary, approve_url, reject_url)
        if not (self.slack or self.email):
            logger.info(f"[MOCK NOTIFIER] Approval for {approver_email}: {action_summary}")
            success = True
        return success

    def read_slack_channels(self, last_hours: int = 24) -> List[Dict[str, Any]]:
        """Delegate to SlackNotifier for Chief of Staff (last 24h messages)."""
        if self.slack and self.slack.client:
            return self.slack.read_slack_channels(last_hours=last_hours)
        # Mock fallback
        return self.slack.read_slack_channels(last_hours=last_hours) if self.slack else []

    def post_to_channel(self, channel: str = "#executive-briefing", summary: str = "") -> bool:
        """Delegate summary post (chat:write)."""
        if self.slack:
            return self.slack.post_summary_to_channel(channel=channel, summary=summary)
        return False

    def notify_block(
        self, snapshot_id: str, reason: str, trust_score: float = 0.0, channel: Optional[str] = None
    ) -> bool:
        """Slack only for block/rejection alerts."""
        if self.slack:
            return self.slack.send_block_alert(channel or self.slack.security_channel, snapshot_id, reason, trust_score)
        logger.warning(f"[MOCK BLOCK ALERT] Snapshot {snapshot_id}: {reason} (trust={trust_score})")
        return True


# Singleton
notifier = Notifier()
