import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.content_models import Post, Comment
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine


class ModerationWorker:
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
        self._projection_engine.register_handler("content_moderated", self._handle_content_moderated)
        self._projection_engine.register_handler("content_restored", self._handle_content_restored)

    def _handle_content_moderated(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            target_id = uuid.UUID(payload["target_id"])
            target_type = payload.get("target_type", "post")
            action = payload.get("action", "hide")

            if target_type == "post":
                post = session.query(Post).filter(Post.post_id == target_id).first()
                if post:
                    if action == "hide":
                        post.status = "hidden"
                    elif action == "remove":
                        post.status = "removed"
                    elif action == "flag":
                        post.status = "flagged"
            elif target_type == "comment":
                comment = session.query(Comment).filter(Comment.comment_id == target_id).first()
                if comment:
                    if action == "hide":
                        comment.status = "hidden"
                    elif action == "remove":
                        comment.status = "removed"
                    elif action == "flag":
                        comment.status = "flagged"

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_content_restored(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            target_id = uuid.UUID(payload["target_id"])
            target_type = payload.get("target_type", "post")

            if target_type == "post":
                post = session.query(Post).filter(Post.post_id == target_id).first()
                if post:
                    post.status = "published"
            elif target_type == "comment":
                comment = session.query(Comment).filter(Comment.comment_id == target_id).first()
                if comment:
                    comment.status = "published"

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()
