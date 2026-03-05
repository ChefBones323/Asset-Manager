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

    def index_content(
        self,
        feed_owner: uuid.UUID,
        content_id: uuid.UUID,
        author_id: uuid.UUID,
        content_type: str = "post",
        policy_scope: str = "default",
        reaction_count: int = 0,
        trust_score: float = 0.0,
        policy_weight: float = 1.0,
        distribution_time: Optional[datetime] = None,
    ) -> dict:
        session = self._get_session()
        try:
            existing = (
                session.query(FeedIndex)
                .filter(
                    FeedIndex.feed_owner == feed_owner,
                    FeedIndex.content_id == content_id,
                )
                .first()
            )
            if existing:
                existing.reaction_count = reaction_count
                existing.trust_score = trust_score
                existing.policy_weight = policy_weight
                session.commit()
                session.refresh(existing)
                return existing.to_dict()

            entry = FeedIndex(
                feed_owner=feed_owner,
                content_id=content_id,
                author_id=author_id,
                content_type=content_type,
                policy_scope=policy_scope,
                reaction_count=reaction_count,
                trust_score=trust_score,
                policy_weight=policy_weight,
                distribution_time=distribution_time or datetime.now(timezone.utc),
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def remove_content(self, feed_owner: uuid.UUID, content_id: uuid.UUID) -> bool:
        session = self._get_session()
        try:
            deleted = (
                session.query(FeedIndex)
                .filter(
                    FeedIndex.feed_owner == feed_owner,
                    FeedIndex.content_id == content_id,
                )
                .delete()
            )
            session.commit()
            return deleted > 0
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()
