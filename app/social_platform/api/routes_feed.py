import uuid
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from app.social_platform.domains.social.feed_service import FeedService
from app.social_platform.workers.feed_generate_worker import FeedGenerateWorker
from app.social_platform.policies.policy_simulator import PolicySimulator

router = APIRouter(prefix="/feed", tags=["feed"])


class PolicySimulationRequest(BaseModel):
    policy_name: str
    rules: list = Field(default_factory=list)
    feed_entries: list = Field(default_factory=list)
    default_weight: float = 1.0
    weights: Optional[dict] = None


@router.get("/user")
def get_user_feed(
    user_id: str = Query(..., description="UUID of the user"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    policy_scope: Optional[str] = Query(None),
    ranked: bool = Query(False, description="Apply deterministic ranking"),
):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    if ranked:
        worker = FeedGenerateWorker()
        feed = worker.generate_feed(uid, limit=limit, offset=offset)
    else:
        service = FeedService()
        feed = service.get_user_feed(uid, limit=limit, offset=offset, policy_scope=policy_scope)

    return {"user_id": user_id, "feed": feed, "count": len(feed), "limit": limit, "offset": offset}


@router.post("/simulate")
def simulate_policy(request: PolicySimulationRequest):
    simulator = PolicySimulator()
    result = simulator.simulate_policy(
        policy_name=request.policy_name,
        rules=request.rules,
        feed_entries=request.feed_entries,
        default_weight=request.default_weight,
        weights=request.weights,
    )
    return result
