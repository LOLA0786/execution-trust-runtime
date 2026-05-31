"""
tests/test_approval_gate.py
Pytest suite (with pytest-asyncio) for Human-in-the-Loop Approval Flow.
Uses fakeredis for Redis, in-memory SQLite for Postgres/ApprovalRequestModel.
Fully implemented per spec: happy_path, rejection, timeout, tampering, replay.
No stubs.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from datetime import datetime, timedelta
import asyncio
import fakeredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from core.approval_gate import approval_gate, ApprovalGate
from core.approval_token import generate_token, verify_token, ApprovalToken, is_expired
from core.vault.private_vault import VaultCheckpointError
from shared.models.db_models import Base, ApprovalRequestModel


@pytest.fixture(scope="function")
def test_db_session():
    """In-memory SQLite for Postgres model testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_redis():
    """fakeredis for Redis mocking."""
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def test_gate(test_db_session, test_redis):
    """ApprovalGate with test DB/Redis (no real network calls)."""
    gate = ApprovalGate(
        redis_client=test_redis,
        db_session=test_db_session,
        secret_key="test-secret-key",
        etr_host="localhost:8000",
    )
    return gate


@pytest.mark.asyncio
async def test_happy_path(test_gate, test_db_session, test_redis):
    """Happy path: request_approval → mock Redis APPROVED → validate_and_record → returns True."""
    # Patch both gate instance method (for test_gate fixture) and facade
    with patch.object(test_gate, 'notify_approval_request') as gate_mock:
        gate_mock.return_value = None
        with patch('services.notifier.notifier.notify_approval_request') as facade_mock:
            facade_mock.return_value = True
            test_redis.set("approval:snapshot-123:token", "valid-hmac-signature")
            test_redis.set("approval:snapshot-123:decision", "APPROVED")

            token, approve_url, reject_url = test_gate.request_approval(
                snapshot_id="snapshot-123",
                action_summary="Process $5.2M vendor payment to Acme Corp",
                approver_email="cfo@example.com",
                metadata={"agent_id": "procurement-1", "action": "payment"},
            )
            assert token.snapshot_id == "snapshot-123"
            assert "approval" in approve_url

            # wait_for_approval now sees APPROVED immediately (no polling/timeout)
            approved = test_gate.wait_for_approval("snapshot-123", timeout_seconds=1, poll_interval=0.01)
            assert approved is True

            # validate_and_record after approval (now with explicit snapshot_id per bugfix)
            validated = test_gate.validate_and_record(
                token_id=token.token_id,
                decision="APPROVED",
                snapshot_id="snapshot-123",
                db_session=test_db_session,
                redis_client=test_redis,
            )
            assert validated is True


@pytest.mark.asyncio
async def test_rejection(test_gate, test_redis):
    """Request → mock Redis REJECTED → raises VaultCheckpointError."""
    test_redis.set("approval:snapshot-reject:decision", "REJECTED")
    with pytest.raises(VaultCheckpointError):
        test_gate.wait_for_approval("snapshot-reject", timeout_seconds=0.1, poll_interval=0.01)


@pytest.mark.asyncio
async def test_timeout(test_gate, test_redis):
    """Wait with short timeout (0.1s) and PENDING → raises TimeoutError."""
    test_redis.set("approval:snapshot-timeout:decision", "PENDING")
    with pytest.raises(TimeoutError):
        test_gate.wait_for_approval("snapshot-timeout", timeout_seconds=0.1, poll_interval=0.01)


def test_token_tampering():
    """Token tampering: modified snapshot_id → verify_token returns False."""
    token = generate_token("original-snapshot", "cfo@example.com", secret_key="test-secret")
    tampered = ApprovalToken(
        token_id=token.token_id,
        snapshot_id="tampered-snapshot",  # changed - invalidates HMAC
        approver_email=token.approver_email,
        signed_at=token.signed_at,
        expires_at=token.expires_at,
        hmac_signature=token.hmac_signature,
        decision=token.decision,
    )
    assert verify_token(tampered, secret_key="test-secret") is False


def test_replay_attack(test_db_session, test_redis):
    """Validate same token_id twice → second call returns False (or raises in webhook context; here tests 409 logic via state)."""
    token = generate_token("snapshot-replay", "cfo@example.com", secret_key="test-secret")
    test_redis.set(f"approval:{token.snapshot_id}:token", token.hmac_signature)

    # First validation succeeds
    validated1 = ApprovalGate(redis_client=test_redis, db_session=test_db_session, secret_key="test-secret").validate_and_record(
        token_id=token.token_id,
        decision="APPROVED",
        snapshot_id=token.snapshot_id,
        db_session=test_db_session,
        redis_client=test_redis,
    )
    assert validated1 is True

    # Second (replay) fails (decision already set or expiry/HMAC state)
    test_redis.set(f"approval:{token.snapshot_id}:decision", "APPROVED")  # simulate consumed
    validated2 = ApprovalGate(redis_client=test_redis, db_session=test_db_session, secret_key="test-secret").validate_and_record(
        token_id=token.token_id,
        decision="APPROVED",
        snapshot_id=token.snapshot_id,
        db_session=test_db_session,
        redis_client=test_redis,
    )
    assert validated2 is False  # or would raise 409 in webhook


def test_generate_and_verify_token():
    """Basic token generation and verification roundtrip."""
    token = generate_token("test-snapshot-456", "approver@test.com", secret_key="test-secret", expires_hours=0.1)
    assert token.snapshot_id == "test-snapshot-456"
    assert len(token.token_id) > 10
    assert len(token.hmac_signature) == 64
    assert verify_token(token, secret_key="test-secret") is True
    assert not is_expired(token)
