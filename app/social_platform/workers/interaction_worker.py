import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.content_models import ReactionSummary, Post
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine


class InteractionWorker:
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
        self._projection_engine.register_handler("reaction_added", self._handle_reaction_added)
        self._projection_engine.register_handler("post_shared", self._handle_post_shared)

    def _handle_reaction_added(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            target_id = uuid.UUID(payload["target_id"])
            target_type = payload.get("target_type", "post")
            reaction_type = payload.get("reaction_type", "like")

            summary = (
                session.query(ReactionSummary)
                .filter(
                    ReactionSummary.target_id == target_id,
                    ReactionSummary.target_type == target_type,
                    ReactionSummary.reaction_type == reaction_type,
                )
                .first()
            )

            if summary:
                summary.count = (summary.count or 0) + 1
            else:
                summary = ReactionSummary(
                    id=uuid.uuid4(),
                    target_id=target_id,
                    target_type=target_type,
                    reaction_type=reaction_type,
                    count=1,
                )
                session.add(summary)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_post_shared(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            post_id = uuid.UUID(payload["post_id"])
            sharer_id = uuid.UUID(payload["sharer_id"])
            share_id = uuid.UUID(payload["share_id"])

            shared_post = Post(
                post_id=share_id,
                author_id=sharer_id,
                content=payload.get("comment", ""),
                content_type="share",
                metadata_={"original_post_id": str(post_id)},
                parent_post_id=post_id,
                status="published",
                created_at=event.timestamp,
            )
            session.add(shared_post)

            summary = (
                session.query(ReactionSummary)
                .filter(
                    ReactionSummary.target_id == post_id,
                    ReactionSummary.target_type == "post",
                    ReactionSummary.reaction_type == "share",
                )
                .first()
            )

            if summary:
                summary.count = (summary.count or 0) + 1
            else:
                summary = ReactionSummary(
                    id=uuid.uuid4(),
                    target_id=post_id,
                    target_type="post",
                    reaction_type="share",
                    count=1,
                )
                session.add(summary)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()
