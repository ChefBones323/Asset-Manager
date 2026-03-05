import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.infrastructure.projection_engine import ProjectionEngine
from app.social_platform.platform.execution_engine import ExecutionEngine
from app.social_platform.domains.social.trust_service import TrustService
from app.social_platform.domains.social.delegation_service import DelegationService
from app.social_platform.domains.social.knowledge_service import KnowledgeService
from app.social_platform.workers.trust_compute_worker import TrustComputeWorker
from app.social_platform.workers.delegation_worker import DelegationWorker
from app.social_platform.workers.knowledge_worker import KnowledgeWorker

router = APIRouter(prefix="/api/trust", tags=["trust"])

_event_store = EventStore()
_projection_engine = ProjectionEngine(_event_store)
_engine = ExecutionEngine(_event_store)
_trust_service = TrustService(_engine)
_delegation_service = DelegationService(_engine)
_knowledge_service = KnowledgeService(_engine)
_trust_worker = TrustComputeWorker(_projection_engine)
_delegation_worker = DelegationWorker(_projection_engine)
_knowledge_worker = KnowledgeWorker(_projection_engine)


class RecordTrustEventRequest(BaseModel):
    actor_id: str
    subject_id: str
    event_type: str
    score_delta: float = Field(default=0.0)
    reason: str = ""
    context: Optional[dict] = None


class GetTrustProfileRequest(BaseModel):
    user_id: str


class DelegateRequest(BaseModel):
    actor_id: str
    delegate_id: str
    domain: str
    scope: str = "full"
    reason: str = ""


class RevokeDelegationRequest(BaseModel):
    actor_id: str
    delegation_id: str
    reason: str = ""


class CheckDelegationRequest(BaseModel):
    delegator_id: str
    delegate_id: str
    domain: str


class CreateArtifactRequest(BaseModel):
    actor_id: str
    title: str
    content: str
    artifact_type: str = "article"
    domain: str = "general"
    metadata: Optional[dict] = None


class AddCitationRequest(BaseModel):
    actor_id: str
    source_artifact_id: str
    cited_artifact_id: str
    context: str = ""


@router.post("/event")
def record_trust_event(req: RecordTrustEventRequest):
    result = _trust_service.record_trust_event(
        actor_id=uuid.UUID(req.actor_id),
        subject_id=uuid.UUID(req.subject_id),
        event_type=req.event_type,
        score_delta=req.score_delta,
        reason=req.reason,
        context=req.context,
    )
    return result


@router.get("/profile/{user_id}")
def get_trust_profile(user_id: str):
    profile = _trust_service.get_trust_profile(uuid.UUID(user_id))
    if not profile:
        return {"user_id": user_id, "trust_score": 0.0, "positive_events": 0, "negative_events": 0, "total_events": 0}
    return profile


@router.post("/compute/{user_id}")
def compute_trust(user_id: str):
    result = _trust_service.compute_trust(uuid.UUID(user_id))
    return result


@router.post("/delegate")
def delegate(req: DelegateRequest):
    try:
        result = _delegation_service.delegate(
            actor_id=uuid.UUID(req.actor_id),
            delegate_id=uuid.UUID(req.delegate_id),
            domain=req.domain,
            scope=req.scope,
            reason=req.reason,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/revoke")
def revoke_delegation(req: RevokeDelegationRequest):
    result = _delegation_service.revoke(
        actor_id=uuid.UUID(req.actor_id),
        delegation_id=uuid.UUID(req.delegation_id),
        reason=req.reason,
    )
    return result


@router.post("/delegation/check")
def check_delegation(req: CheckDelegationRequest):
    path = _delegation_service.check_delegation_path(
        delegator_id=uuid.UUID(req.delegator_id),
        delegate_id=uuid.UUID(req.delegate_id),
        domain=req.domain,
    )
    return {"path": path, "has_delegation": len(path) > 0}


@router.post("/delegation/loop-check")
def check_delegation_loop(req: CheckDelegationRequest):
    would_loop = _delegation_service.prevent_loops(
        delegator_id=uuid.UUID(req.delegator_id),
        delegate_id=uuid.UUID(req.delegate_id),
        domain=req.domain,
    )
    return {"would_create_loop": would_loop}


@router.post("/knowledge/artifact")
def create_artifact(req: CreateArtifactRequest):
    result = _knowledge_service.create_artifact(
        actor_id=uuid.UUID(req.actor_id),
        title=req.title,
        content=req.content,
        artifact_type=req.artifact_type,
        domain=req.domain,
        metadata=req.metadata,
    )
    return result


@router.get("/knowledge/artifact/{artifact_id}")
def get_artifact(artifact_id: str):
    artifact = _knowledge_service.get_artifact(uuid.UUID(artifact_id))
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.post("/knowledge/citation")
def add_citation(req: AddCitationRequest):
    result = _knowledge_service.add_citation(
        actor_id=uuid.UUID(req.actor_id),
        source_artifact_id=uuid.UUID(req.source_artifact_id),
        cited_artifact_id=uuid.UUID(req.cited_artifact_id),
        context=req.context,
    )
    return result


@router.post("/knowledge/score/{artifact_id}")
def compute_knowledge_score(artifact_id: str):
    result = _knowledge_service.compute_knowledge_score(uuid.UUID(artifact_id))
    return result
