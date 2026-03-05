import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.governance_models import GovernanceProposal, GovernanceVote
from app.social_platform.platform.execution_engine import ExecutionEngine


class GovernanceService:
    DOMAIN = "governance"

    def __init__(self, execution_engine: ExecutionEngine, session: Optional[Session] = None):
        self._engine = execution_engine
        self._session = session
        self._engine.register_executor("create_governance_proposal", self._execute_create_governance_proposal)
        self._engine.register_executor("governance_vote", self._execute_governance_vote)
        self._engine.register_executor("execute_governance", self._execute_governance)

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def create_governance_proposal(
        self,
        actor_id: uuid.UUID,
        title: str,
        description: str,
        proposal_type: str = "policy_change",
        domain: str = "general",
        payload: Optional[dict] = None,
        quorum: int = 1,
        approval_threshold: float = 0.5,
    ) -> dict:
        proposal_payload = {
            "title": title,
            "description": description,
            "proposal_type": proposal_type,
            "domain": domain,
            "payload": payload or {},
            "quorum": quorum,
            "approval_threshold": approval_threshold,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="create_governance_proposal",
            payload=proposal_payload,
            description=f"Governance proposal: {title[:50]}",
        )

    def vote(
        self,
        actor_id: uuid.UUID,
        proposal_id: uuid.UUID,
        vote: str,
        weight: float = 1.0,
        reason: str = "",
    ) -> dict:
        if vote not in ("for", "against", "abstain"):
            raise ValueError("Vote must be 'for', 'against', or 'abstain'")

        payload = {
            "proposal_id": str(proposal_id),
            "vote": vote,
            "weight": weight,
            "reason": reason,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="governance_vote",
            payload=payload,
            description=f"Vote {vote} on proposal {proposal_id}",
        )

    def tally(self, proposal_id: uuid.UUID) -> dict:
        session = self._get_session()
        try:
            proposal = (
                session.query(GovernanceProposal)
                .filter(GovernanceProposal.proposal_id == proposal_id)
                .first()
            )
            if not proposal:
                return {"proposal_id": str(proposal_id), "status": "not_found"}

            votes = (
                session.query(GovernanceVote)
                .filter(GovernanceVote.proposal_id == proposal_id)
                .all()
            )

            votes_for = sum(v.weight for v in votes if v.vote == "for")
            votes_against = sum(v.weight for v in votes if v.vote == "against")
            total_votes = len(votes)

            quorum_met = total_votes >= proposal.quorum
            total_weight = votes_for + votes_against
            approval_ratio = votes_for / total_weight if total_weight > 0 else 0.0
            approved = quorum_met and approval_ratio >= proposal.approval_threshold

            return {
                "proposal_id": str(proposal_id),
                "votes_for": votes_for,
                "votes_against": votes_against,
                "total_votes": total_votes,
                "quorum_met": quorum_met,
                "approval_ratio": approval_ratio,
                "approved": approved,
                "status": proposal.status,
            }
        finally:
            if self._should_close():
                session.close()

    def execute_approved(self, proposal_id: uuid.UUID, actor_id: uuid.UUID) -> dict:
        tally_result = self.tally(proposal_id)
        if not tally_result.get("approved"):
            raise ValueError(f"Proposal {proposal_id} is not approved (quorum or threshold not met)")

        payload = {
            "governance_proposal_id": str(proposal_id),
            "tally": tally_result,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="execute_governance",
            payload=payload,
            description=f"Execute approved governance proposal {proposal_id}",
        )

    def get_proposal(self, proposal_id: uuid.UUID) -> Optional[dict]:
        session = self._get_session()
        try:
            proposal = (
                session.query(GovernanceProposal)
                .filter(GovernanceProposal.proposal_id == proposal_id)
                .first()
            )
            return proposal.to_dict() if proposal else None
        finally:
            if self._should_close():
                session.close()

    def list_proposals(
        self,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        session = self._get_session()
        try:
            query = session.query(GovernanceProposal)
            if status:
                query = query.filter(GovernanceProposal.status == status)
            if domain:
                query = query.filter(GovernanceProposal.domain == domain)
            proposals = (
                query.order_by(GovernanceProposal.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [p.to_dict() for p in proposals]
        finally:
            if self._should_close():
                session.close()

    def _execute_create_governance_proposal(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))
        gov_proposal_id = uuid.uuid4()

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="governance_proposal_created",
            actor_id=actor_id,
            payload={
                "governance_proposal_id": str(gov_proposal_id),
                "author_id": str(actor_id),
                "title": payload.get("title", ""),
                "description": payload.get("description", ""),
                "proposal_type": payload.get("proposal_type", "policy_change"),
                "domain": payload.get("domain", "general"),
                "payload": payload.get("payload", {}),
                "quorum": payload.get("quorum", 1),
                "approval_threshold": payload.get("approval_threshold", 0.5),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"governance_proposal_id": str(gov_proposal_id), "status": "created"}

    def _execute_governance_vote(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))
        vote_id = uuid.uuid4()

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="governance_vote_cast",
            actor_id=actor_id,
            payload={
                "vote_id": str(vote_id),
                "governance_proposal_id": payload.get("proposal_id"),
                "voter_id": str(actor_id),
                "vote": payload.get("vote", "abstain"),
                "weight": payload.get("weight", 1.0),
                "reason": payload.get("reason", ""),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"vote_id": str(vote_id), "status": "cast"}

    def _execute_governance(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="governance_executed",
            actor_id=actor_id,
            payload={
                "governance_proposal_id": payload.get("governance_proposal_id"),
                "tally": payload.get("tally", {}),
                "executor_id": str(actor_id),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"governance_proposal_id": payload.get("governance_proposal_id"), "status": "executed"}
