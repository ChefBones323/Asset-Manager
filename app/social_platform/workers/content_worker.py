import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.content_models import Post, Comment, Thread
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine


class ContentWorker:
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
        self._projection_engine.register_handler("content_created", self._handle_content_created)
        self._projection_engine.register_handler("comment_created", self._handle_comment_created)

    def _handle_content_created(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            post_id = uuid.UUID(payload["post_id"])
            author_id = uuid.UUID(payload["author_id"])
            thread_id = uuid.uuid4()

            post = Post(
                post_id=post_id,
                author_id=author_id,
                content=payload.get("content", ""),
                content_type=payload.get("content_type", "text"),
                metadata_=payload.get("metadata", {}),
                thread_id=thread_id,
                status="published",
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(post)

            thread = Thread(
                thread_id=thread_id,
                root_post_id=post_id,
                title=payload.get("content", "")[:200],
                participant_count=1,
                reply_count=0,
                last_activity_at=event.timestamp or datetime.now(timezone.utc),
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(thread)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_comment_created(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            comment_id = uuid.UUID(payload["comment_id"])
            post_id = uuid.UUID(payload["post_id"])
            author_id = uuid.UUID(payload["author_id"])
            parent_comment_id = uuid.UUID(payload["parent_comment_id"]) if payload.get("parent_comment_id") else None

            comment = Comment(
                comment_id=comment_id,
                post_id=post_id,
                author_id=author_id,
                content=payload.get("content", ""),
                parent_comment_id=parent_comment_id,
                status="published",
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(comment)

            post = session.query(Post).filter(Post.post_id == post_id).first()
            if post and post.thread_id:
                thread = session.query(Thread).filter(Thread.thread_id == post.thread_id).first()
                if thread:
                    thread.reply_count = (thread.reply_count or 0) + 1
                    thread.last_activity_at = event.timestamp or datetime.now(timezone.utc)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()
