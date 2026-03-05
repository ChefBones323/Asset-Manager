import uuid
from datetime import datetime, timezone
from typing import Optional

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.platform.proposal_service import ProposalService


class ApprovalService:
    def __init__(self, event_store: EventStore, proposal_service: ProposalService):
        self._event_store = event_store
        self._proposal_service = proposal_service

    def approve_proposal(self, proposal_id: str, approver_id: uuid.UUID, reason: str = "") -> Optional[dict]:
        proposal = self._proposal_service.get_proposal(proposal_id)
        if not proposal:
            return None
        if proposal["status"] != "pending":
            raise ValueError(f"Cannot approve proposal in status '{proposal['status']}'")

        now = datetime.now(timezone.utc).isoformat()
        updated = self._proposal_service.update_proposal_status(
            proposal_id, "approved", approved_at=now, approver_id=str(approver_id)
        )

        self._event_store.append_event(
            domain="platform",
            event_type="proposal_approved",
            actor_id=approver_id,
            payload={"proposal_id": proposal_id, "reason": reason},
        )
        return updated

    def reject_proposal(self, proposal_id: str, rejector_id: uuid.UUID, reason: str = "") -> Optional[dict]:
        proposal = self._proposal_service.get_proposal(proposal_id)
        if not proposal:
            return None
        if proposal["status"] != "pending":
            raise ValueError(f"Cannot reject proposal in status '{proposal['status']}'")

        now = datetime.now(timezone.utc).isoformat()
        updated = self._proposal_service.update_proposal_status(
            proposal_id, "rejected", rejected_at=now, rejection_reason=reason, rejector_id=str(rejector_id)
        )

        self._event_store.append_event(
            domain="platform",
            event_type="proposal_rejected",
            actor_id=rejector_id,
            payload={"proposal_id": proposal_id, "reason": reason},
        )
        return updated

    def is_approved(self, proposal_id: str) -> bool:
        proposal = self._proposal_service.get_proposal(proposal_id)
        if not proposal:
            return False
        return proposal["status"] == "approved"
