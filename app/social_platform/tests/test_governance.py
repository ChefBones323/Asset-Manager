import uuid
import pytest
from unittest.mock import MagicMock

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.platform.execution_engine import ExecutionEngine
from app.social_platform.domains.social.governance_service import GovernanceService


class TestGovernanceService:
    def _make_service(self):
        session = MagicMock()
        event_store = EventStore(session=session)
        engine = ExecutionEngine(event_store)
        service = GovernanceService(engine, session=session)
        return service, engine, session

    def test_create_governance_proposal(self):
        service, engine, _ = self._make_service()
        actor_id = uuid.uuid4()

        result = service.create_governance_proposal(
            actor_id=actor_id,
            title="Test Proposal",
            description="A test governance proposal",
            proposal_type="policy_change",
            domain="general",
        )

        assert result["status"] == "pending"
        assert result["domain"] == "governance"
        assert result["action"] == "create_governance_proposal"

    def test_vote_valid_values(self):
        service, engine, _ = self._make_service()
        actor_id = uuid.uuid4()
        proposal_id = uuid.uuid4()

        for vote_val in ("for", "against", "abstain"):
            result = service.vote(
                actor_id=actor_id,
                proposal_id=proposal_id,
                vote=vote_val,
            )
            assert result["status"] == "pending"

    def test_vote_invalid_value_raises(self):
        service, engine, _ = self._make_service()
        actor_id = uuid.uuid4()
        proposal_id = uuid.uuid4()

        with pytest.raises(ValueError, match="Vote must be"):
            service.vote(
                actor_id=actor_id,
                proposal_id=proposal_id,
                vote="maybe",
            )

    def test_executors_registered(self):
        service, engine, _ = self._make_service()
        assert "create_governance_proposal" in engine._executors
        assert "governance_vote" in engine._executors
        assert "execute_governance" in engine._executors
