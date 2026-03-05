import uuid
from typing import Optional, List

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.content_models import Post, Comment, Thread


class DiscussionService:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def get_thread(self, thread_id: uuid.UUID) -> Optional[dict]:
        session = self._get_session()
        try:
            thread = session.query(Thread).filter(Thread.thread_id == thread_id).first()
            if not thread:
                return None

            root_post = session.query(Post).filter(Post.post_id == thread.root_post_id).first()
            replies = (
                session.query(Post)
                .filter(Post.thread_id == thread_id, Post.post_id != thread.root_post_id)
                .order_by(Post.created_at.asc())
                .all()
            )
            comments = (
                session.query(Comment)
                .filter(Comment.post_id == thread.root_post_id)
                .order_by(Comment.created_at.asc())
                .all()
            )

            return {
                "thread": thread.to_dict(),
                "root_post": root_post.to_dict() if root_post else None,
                "replies": [r.to_dict() for r in replies],
                "comments": [c.to_dict() for c in comments],
            }
        finally:
            if self._should_close():
                session.close()

    def list_discussions(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        session = self._get_session()
        try:
            threads = (
                session.query(Thread)
                .order_by(Thread.last_activity_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [t.to_dict() for t in threads]
        finally:
            if self._should_close():
                session.close()
