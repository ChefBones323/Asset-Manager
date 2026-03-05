import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.social_platform.models.base import SessionLocal
from app.social_platform.models.feed_models import FeedIndex


class FeedService:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def get_user_feed(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        policy_scope: Optional[str] = None,
    ) -> List[dict]:
        session = self._get_session()
        try:
            query = session.query(FeedIndex).filter(FeedIndex.feed_owner == user_id)
            if policy_scope:
                query = query.filter(FeedIndex.policy_scope == policy_scope)

            entries = (
                query.order_by(FeedIndex.distribution_time.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return [entry.to_dict() for entry in entries]
        finally:
            if self._should_close():
                session.close()

    def get_feed_entry(
        self,
        feed_owner: uuid.UUID,
        content_id: uuid.UUID,
    ) -> Optional[dict]:
        session = self._get_session()
        try:
            entry = (
                session.query(FeedIndex)
                .filter(
                    FeedIndex.feed_owner == feed_owner,
                    FeedIndex.content_id == content_id,
                )
                .first()
            )
            return entry.to_dict() if entry else None
        finally:
            if self._should_close():
                session.close()

    def count_feed_entries(self, user_id: uuid.UUID) -> int:
        session = self._get_session()
        try:
            return session.query(FeedIndex).filter(FeedIndex.feed_owner == user_id).count()
        finally:
            if self._should_close():
                session.close()
