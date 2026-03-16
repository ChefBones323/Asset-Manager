import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.infrastructure.projection_engine import ProjectionEngine
from app.social_platform.platform.execution_engine import ExecutionEngine
from app.social_platform.domains.social.governance_service import GovernanceService
from app.social_platform.workers.policy_worker import PolicyWorker
from app.social_platform.workers.moderation_worker import ModerationWorker

router = APIRouter(prefix="/api/governance", tags=["governance"])

_event_store = EventStore()
_projection_engine = ProjectionEngine(_event_store)
_execution_engine = ExecutionEngine(_event_store)
_governance_service = GovernanceService(_execution_engine)
_policy_worker = PolicyWorker(_projection_engine)
_moderation_worker = ModerationWorker(_projection_engine)


class CreateGovernanceProposalRequest(BaseModel):
    actor_id: str
    title: str
    description: str
    proposal_type: str = "policy_change"
    domain: str = "general"
    payload: Optional[dict] = Field(default_factory=dict)
    quorum: int = 1
    approval_threshold: float = 0.5


class VoteRequest(BaseModel):
    actor_id: str
    proposal_id: str
    vote: str
    weight: float = 1.0
    reason: str = ""


class ExecuteApprovedRequest(BaseModel):
    actor_id: str
    proposal_id: str
    async_enqueue: bool = False


@router.post("/proposal")
def create_governance_proposal(request: CreateGovernanceProposalRequest):
    try:
        result = _governance_service.create_governance_proposal(
            actor_id=uuid.UUID(request.actor_id),
            title=request.title,
            description=request.description,
            proposal_type=request.proposal_type,
            domain=request.domain,
            payload=request.payload,
            quorum=request.quorum,
            approval_threshold=request.approval_threshold,
        )
        return {"status": "proposal_created", "proposal": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/vote")
def vote(request: VoteRequest):
    try:
        result = _governance_service.vote(
            actor_id=uuid.UUID(request.actor_id),
            proposal_id=uuid.UUID(request.proposal_id),
            vote=request.vote,
            weight=request.weight,
            reason=request.reason,
        )
        return {"status": "vote_cast", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/proposal/{proposal_id}")
def get_governance_proposal(proposal_id: str):
    try:
        result = _governance_service.get_proposal(uuid.UUID(proposal_id))
        if not result:
            raise HTTPException(status_code=404, detail="Governance proposal not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/proposals")
def list_governance_proposals(
    status: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    try:
        return _governance_service.list_proposals(
            status=status, domain=domain, limit=limit, offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tally/{proposal_id}")
def tally_votes(proposal_id: str):
    try:
        result = _governance_service.tally(uuid.UUID(proposal_id))
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/execute")
def execute_approved(request: ExecuteApprovedRequest):
    try:
        if request.async_enqueue:
            enqueue_result = _execution_engine.enqueue(request.proposal_id)
            return {"status": "enqueued", "result": enqueue_result}

        result = _governance_service.execute_approved(
            proposal_id=uuid.UUID(request.proposal_id),
            actor_id=uuid.UUID(request.actor_id),
        )
        return {"status": "executed", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
