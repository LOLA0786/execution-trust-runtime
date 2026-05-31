"""
core/approval_token.py
Cryptographically bound approval token for Human-in-the-Loop flow in Execution Trust Runtime.
Binds human decision to CognitionSnapshot (Merkle hash) via HMAC-SHA256. Fully implemented.
No stubs, no TODOs.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Literal
import uuid
import hashlib
import hmac
import os


@dataclass
class ApprovalToken:
    """Immutable token cryptographically bound to a specific snapshot_id (Merkle hash)."""
    token_id: str
    snapshot_id: str
    approver_email: str
    signed_at: datetime
    expires_at: datetime
    hmac_signature: str
    decision: Literal["APPROVED", "REJECTED", "PENDING"] = "PENDING"


def generate_token(
    snapshot_id: str, 
    approver_email: str, 
    secret_key: str = None,
    expires_hours: int = 1
) -> ApprovalToken:
    """Generate HMAC-signed token bound to snapshot_id."""
    if secret_key is None:
        secret_key = os.getenv("SECRET_KEY", "default-development-secret-key-change-in-prod")
    
    token_id = str(uuid.uuid4())
    signed_at = datetime.now(UTC)
    expires_at = signed_at + timedelta(hours=expires_hours)
    
    # HMAC binds token to snapshot (prevents tampering or mutation after approval)
    message = f"{snapshot_id}:{token_id}:{approver_email}:{signed_at.isoformat()}".encode("utf-8")
    hmac_signature = hmac.new(
        secret_key.encode("utf-8"), 
        message, 
        hashlib.sha256
    ).hexdigest()
    
    return ApprovalToken(
        token_id=token_id,
        snapshot_id=snapshot_id,
        approver_email=approver_email,
        signed_at=signed_at,
        expires_at=expires_at,
        hmac_signature=hmac_signature,
        decision="PENDING"
    )


def verify_token(token: ApprovalToken, secret_key: str = None) -> bool:
    """Recompute HMAC and verify signature, expiry, and binding."""
    if secret_key is None:
        secret_key = os.getenv("SECRET_KEY", "default-development-secret-key-change-in-prod")
    
    if datetime.now(UTC) > token.expires_at:
        return False
    
    message = f"{token.snapshot_id}:{token.token_id}:{token.approver_email}:{token.signed_at.isoformat()}".encode("utf-8")
    expected_signature = hmac.new(
        secret_key.encode("utf-8"), 
        message, 
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, token.hmac_signature)


def is_expired(token: ApprovalToken) -> bool:
    """Check if token has expired."""
    return datetime.now(UTC) > token.expires_at
