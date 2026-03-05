import uuid
import pytest
from unittest.mock import MagicMock, patch

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.platform.execution_engine import ExecutionEngine


class TestExecutionEngine:
    def _make_engine(self):
        event_store = MagicMock(spec=EventStore)
        event_store.get_events_by_domain.return_value = []
        engine = ExecutionEngine(event_store)
        return engine, event_store

    def test_engine_has_services(self):
        engine, _ = self._make_engine()
        assert engine.proposal_service is not None
        assert engine.approval_service is not None
        assert engine.manifest_compiler is not None
        assert engine.lease_manager is not None
        assert engine.audit_logger is not None

    def test_submit_proposal(self):
        engine, session = self._make_engine()
        actor_id = uuid.uuid4()

        proposal = engine.submit_proposal(
            actor_id=actor_id,
            domain="test",
            action="test_action",
            payload={"key": "value"},
            description="Test proposal",
        )

        assert proposal["domain"] == "test"
        assert proposal["action"] == "test_action"
        assert proposal["status"] == "pending"
        assert "proposal_id" in proposal

    def test_approve_proposal(self):
        engine, session = self._make_engine()
        actor_id = uuid.uuid4()
        approver_id = uuid.uuid4()

        proposal = engine.submit_proposal(
            actor_id=actor_id,
            domain="test",
            action="test_action",
            payload={},
        )

        result = engine.approve(proposal["proposal_id"], approver_id, "Looks good")
        assert result is not None

    def test_reject_proposal(self):
        engine, session = self._make_engine()
        actor_id = uuid.uuid4()
        rejector_id = uuid.uuid4()

        proposal = engine.submit_proposal(
            actor_id=actor_id,
            domain="test",
            action="test_action",
            payload={},
        )

        result = engine.reject(proposal["proposal_id"], rejector_id, "Not approved")
        assert result is not None

    def test_register_executor(self):
        engine, _ = self._make_engine()
        executor_fn = MagicMock(return_value={"status": "done"})
        engine.register_executor("custom_action", executor_fn)
        assert "custom_action" in engine._executors

    def test_execute_unapproved_raises(self):
        engine, session = self._make_engine()
        actor_id = uuid.uuid4()

        proposal = engine.submit_proposal(
            actor_id=actor_id,
            domain="test",
            action="test_action",
            payload={},
        )

        with pytest.raises(ValueError, match="not approved"):
            engine.execute(proposal["proposal_id"], "worker-1")

    def test_execute_nonexistent_raises(self):
        engine, _ = self._make_engine()
        with pytest.raises(ValueError, match="not found"):
            engine.execute(str(uuid.uuid4()), "worker-1")

    def test_audit_trail_after_submit(self):
        engine, session = self._make_engine()
        actor_id = uuid.uuid4()

        engine.submit_proposal(
            actor_id=actor_id,
            domain="test",
            action="test_action",
            payload={},
        )

        audit_events = [
            call for call in engine._event_store.append_event.call_args_list
            if call[1].get("domain") == "audit" or (call[0] and call[0][0] == "audit")
        ]
        assert len(audit_events) >= 1
