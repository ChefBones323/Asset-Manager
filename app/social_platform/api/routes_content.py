import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.infrastructure.projection_engine import ProjectionEngine
from app.social_platform.platform.execution_engine import ExecutionEngine
from app.social_platform.domains.social.content_service import ContentService
from app.social_platform.domains.social.discussion_service import DiscussionService
from app.social_platform.workers.content_worker import ContentWorker
from app.social_platform.workers.interaction_worker import InteractionWorker
from app.social_platform.workers.feed_index_worker import FeedIndexWorker

router = APIRouter(prefix="/content", tags=["content"])

_event_store = EventStore()
_projection_engine = ProjectionEngine(_event_store)
_execution_engine = ExecutionEngine(_event_store)
_content_service = ContentService(_execution_engine)
_discussion_service = DiscussionService()
_content_worker = ContentWorker(_projection_engine)
_interaction_worker = InteractionWorker(_projection_engine)
_feed_index_worker = FeedIndexWorker(_projection_engine)


class CreatePostRequest(BaseModel):
    actor_id: str
    content: str
    content_type: str = "text"
    metadata: Optional[dict] = Field(default_factory=dict)


class CreateCommentRequest(BaseModel):
    actor_id: str
    post_id: str
    content: str
    parent_comment_id: Optional[str] = None


class AddReactionRequest(BaseModel):
    actor_id: str
    target_id: str
    target_type: str = "post"
    reaction_type: str = "like"


class SharePostRequest(BaseModel):
    actor_id: str
    post_id: str
    comment: str = ""


@router.post("/post")
def create_post(request: CreatePostRequest):
    try:
        proposal = _content_service.create_post(
            actor_id=uuid.UUID(request.actor_id),
            content=request.content,
            content_type=request.content_type,
            metadata=request.metadata,
        )
        return {"status": "proposal_created", "proposal": proposal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/comment")
def create_comment(request: CreateCommentRequest):
    try:
        parent_comment_id = uuid.UUID(request.parent_comment_id) if request.parent_comment_id else None
        proposal = _content_service.create_comment(
            actor_id=uuid.UUID(request.actor_id),
            post_id=uuid.UUID(request.post_id),
            content=request.content,
            parent_comment_id=parent_comment_id,
        )
        return {"status": "proposal_created", "proposal": proposal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/react")
def add_reaction(request: AddReactionRequest):
    try:
        proposal = _content_service.add_reaction(
            actor_id=uuid.UUID(request.actor_id),
            target_id=uuid.UUID(request.target_id),
            target_type=request.target_type,
            reaction_type=request.reaction_type,
        )
        return {"status": "proposal_created", "proposal": proposal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/share")
def share_post(request: SharePostRequest):
    try:
        proposal = _content_service.share_post(
            actor_id=uuid.UUID(request.actor_id),
            post_id=uuid.UUID(request.post_id),
            comment=request.comment,
        )
        return {"status": "proposal_created", "proposal": proposal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/thread/{thread_id}")
def get_thread(thread_id: str):
    try:
        result = _discussion_service.get_thread(uuid.UUID(thread_id))
        if not result:
            raise HTTPException(status_code=404, detail="Thread not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/discussions")
def list_discussions(limit: int = 50, offset: int = 0):
    try:
        return _discussion_service.list_discussions(limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
