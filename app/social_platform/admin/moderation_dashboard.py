from typing import Optional, List

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.content_models import Post, Comment


class ModerationDashboard:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def get_overview(self) -> dict:
        session = self._get_session()
        try:
            flagged_posts = session.query(Post).filter(Post.status == "flagged").count()
            hidden_posts = session.query(Post).filter(Post.status == "hidden").count()
            removed_posts = session.query(Post).filter(Post.status == "removed").count()
            flagged_comments = session.query(Comment).filter(Comment.status == "flagged").count()
            hidden_comments = session.query(Comment).filter(Comment.status == "hidden").count()
            removed_comments = session.query(Comment).filter(Comment.status == "removed").count()
            return {
                "flagged_posts": flagged_posts,
                "hidden_posts": hidden_posts,
                "removed_posts": removed_posts,
                "flagged_comments": flagged_comments,
                "hidden_comments": hidden_comments,
                "removed_comments": removed_comments,
                "total_moderated": flagged_posts + hidden_posts + removed_posts + flagged_comments + hidden_comments + removed_comments,
            }
        finally:
            if self._should_close():
                session.close()

    def get_flagged_content(self, limit: int = 50) -> dict:
        session = self._get_session()
        try:
            posts = (
                session.query(Post)
                .filter(Post.status == "flagged")
                .order_by(Post.created_at.desc())
                .limit(limit)
                .all()
            )
            comments = (
                session.query(Comment)
                .filter(Comment.status == "flagged")
                .order_by(Comment.created_at.desc())
                .limit(limit)
                .all()
            )
            return {
                "posts": [p.to_dict() for p in posts],
                "comments": [c.to_dict() for c in comments],
            }
        finally:
            if self._should_close():
                session.close()
