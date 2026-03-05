import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.social_platform.infrastructure.event_store import EventStore


class ProposalService:
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._proposals: Dict[str, Dict[str, Any]] = {}

    def create_proposal(
        self,
        actor_id: uuid.UUID,
        domain: str,
        action: str,
        payload: dict,
        description: str = "",
    ) -> dict:
        proposal_id = str(uuid.uuid4())
        proposal = {
            "proposal_id": proposal_id,
            "actor_id": str(actor_id),
            "domain": domain,
            "action": action,
            "payload": payload,
            "description": description,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "approved_at": None,
            "rejected_at": None,
            "rejection_reason": None,
        }
        self._proposals[proposal_id] = proposal

        self._event_store.append_event(
            domain="platform",
            event_type="proposal_created",
            actor_id=actor_id,
            payload={"proposal_id": proposal_id, "domain": domain, "action": action, "description": description},
        )
        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[dict]:
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 50,
    ) -> List[dict]:
        results = list(self._proposals.values())
        if status:
            results = [p for p in results if p["status"] == status]
        if domain:
            results = [p for p in results if p["domain"] == domain]
        results.sort(key=lambda p: p["created_at"], reverse=True)
        return results[:limit]

    def update_proposal_status(self, proposal_id: str, status: str, **kwargs) -> Optional[dict]:
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None
        proposal["status"] = status
        for key, value in kwargs.items():
            proposal[key] = value
        return proposal
