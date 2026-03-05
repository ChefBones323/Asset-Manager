from typing import Optional, List
from app.social_platform.domains.social.governance_service import GovernanceService


class GovernanceDashboard:
    def __init__(self, governance_service: GovernanceService):
        self._governance_service = governance_service

    def get_overview(self) -> dict:
        open_proposals = self._governance_service.list_proposals(status="open")
        executed_proposals = self._governance_service.list_proposals(status="executed")
        return {
            "open_proposals_count": len(open_proposals),
            "executed_proposals_count": len(executed_proposals),
            "open_proposals": open_proposals[:10],
            "recent_executed": executed_proposals[:10],
        }

    def get_proposal_detail(self, proposal_id) -> Optional[dict]:
        return self._governance_service.get_proposal(proposal_id)

    def list_proposals_by_status(self, status: str, limit: int = 50) -> List[dict]:
        return self._governance_service.list_proposals(status=status, limit=limit)
