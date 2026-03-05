import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.governance_models import GovernanceProposal
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine
from app.social_platform.policies.policy_registry import get_global_registry
from app.social_platform.policies.policy_validator import validate_policy, PolicyValidationError


class PolicyWorker:
    def __init__(self, projection_engine: ProjectionEngine, session: Optional[Session] = None):
        self._projection_engine = projection_engine
        self._session = session
        self._register_handlers()

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def _register_handlers(self):
        self._projection_engine.register_handler("governance_proposal_created", self._handle_proposal_created)
        self._projection_engine.register_handler("governance_vote_cast", self._handle_vote_cast)
        self._projection_engine.register_handler("governance_executed", self._handle_governance_executed)
        self._projection_engine.register_handler("feed_policy_proposed", self._handle_feed_policy_proposed)
        self._projection_engine.register_handler("feed_policy_approved", self._handle_feed_policy_approved)

    def _handle_proposal_created(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}

            proposal = GovernanceProposal(
                proposal_id=uuid.UUID(payload["governance_proposal_id"]),
                author_id=uuid.UUID(payload["author_id"]),
                title=payload.get("title", ""),
                description=payload.get("description", ""),
                proposal_type=payload.get("proposal_type", "policy_change"),
                domain=payload.get("domain", "general"),
                payload=payload.get("payload", {}),
                status="open",
                quorum=payload.get("quorum", 1),
                approval_threshold=payload.get("approval_threshold", 0.5),
                votes_for=0,
                votes_against=0,
                total_votes=0,
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(proposal)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_vote_cast(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            from app.social_platform.models.governance_models import GovernanceVote

            vote = GovernanceVote(
                vote_id=uuid.UUID(payload["vote_id"]),
                proposal_id=uuid.UUID(payload["governance_proposal_id"]),
                voter_id=uuid.UUID(payload["voter_id"]),
                vote=payload.get("vote", "abstain"),
                weight=payload.get("weight", 1.0),
                reason=payload.get("reason", ""),
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(vote)

            proposal_id = uuid.UUID(payload["governance_proposal_id"])
            proposal = (
                session.query(GovernanceProposal)
                .filter(GovernanceProposal.proposal_id == proposal_id)
                .first()
            )
            if proposal:
                proposal.total_votes = (proposal.total_votes or 0) + 1
                vote_direction = payload.get("vote", "abstain")
                weight = payload.get("weight", 1.0)
                if vote_direction == "for":
                    proposal.votes_for = (proposal.votes_for or 0) + int(weight)
                elif vote_direction == "against":
                    proposal.votes_against = (proposal.votes_against or 0) + int(weight)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_governance_executed(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            proposal_id = uuid.UUID(payload["governance_proposal_id"])

            proposal = (
                session.query(GovernanceProposal)
                .filter(GovernanceProposal.proposal_id == proposal_id)
                .first()
            )
            if proposal:
                proposal.status = "executed"
                proposal.execution_result = payload.get("tally", {})
                proposal.closed_at = event.timestamp or datetime.now(timezone.utc)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_feed_policy_proposed(self, event: Event):
        payload = event.payload or {}
        policy_data = payload.get("policy", {})

        if not policy_data:
            return

        registry = get_global_registry()
        try:
            from app.social_platform.policies.policy_registry import PolicyAlreadyPublishedError
            registry.register_policy(policy_data, approved=False)
        except PolicyAlreadyPublishedError:
            pass

    def _handle_feed_policy_approved(self, event: Event):
        payload = event.payload or {}
        policy_id = payload.get("policy_id")

        if not policy_id:
            return

        registry = get_global_registry()
        try:
            from app.social_platform.policies.policy_registry import PolicyNotFoundError
            registry.approve_policy(policy_id)
        except PolicyNotFoundError:
            pass
