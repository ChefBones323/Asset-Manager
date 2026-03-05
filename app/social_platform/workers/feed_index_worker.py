import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.social_platform.models.base import SessionLocal
from app.social_platform.models.feed_models import FeedIndex
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine


class FeedIndexWorker:
    def __init__(self, projection_engine: ProjectionEngine, session: Optional[Session] = None):
        self._projection_engine = projection_engine
        self._session = session
        self._register_handlers()

    def _register_handlers(self):
        self._projection_engine.register_handler("content_created", self._handle_event_dispatch)
        self._projection_engine.register_handler("post_shared", self._handle_event_dispatch)
        self._projection_engine.register_handler("reaction_added", self._handle_event_dispatch)
        self._projection_engine.register_handler("content_removed", self._handle_event_dispatch)

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def _handle_event_dispatch(self, event: Event):
        self.handle_event(event)

    def handle_event(self, event) -> dict:
        event_type = event.event_type if hasattr(event, "event_type") else event.get("event_type", "")
        payload = event.payload if hasattr(event, "payload") else event.get("payload", {})
        actor_id = event.actor_id if hasattr(event, "actor_id") else event.get("actor_id")

        if event_type == "content_created":
            return self._index_new_content(payload, actor_id)
        elif event_type == "post_shared":
            return self._index_shared_content(payload, actor_id)
        elif event_type == "reaction_added":
            return self._update_reaction_count(payload)
        elif event_type == "content_removed":
            return self._remove_content(payload)

        return {"status": "ignored", "event_type": event_type}

    def _upsert_feed_entry(
        self,
        session: Session,
        feed_owner: uuid.UUID,
        content_id: uuid.UUID,
        author_id: uuid.UUID,
        content_type: str = "post",
        policy_scope: str = "default",
        reaction_count: int = 0,
        trust_score: float = 0.0,
        policy_weight: float = 1.0,
        distribution_time: Optional[datetime] = None,
    ) -> None:
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
        else:
            entry = FeedIndex(
                feed_owner=feed_owner,
                content_id=content_id,
                author_id=author_id,
                content_type=content_type,
                policy_scope=policy_scope,
                reaction_count=reaction_count,
                trust_score=trust_score,
                policy_weight=policy_weight,
                distribution_time=distribution_time or datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(entry)

    def _index_new_content(self, payload: dict, actor_id) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        author_id = uuid.UUID(str(actor_id))
        followers = payload.get("followers", [])

        session = self._get_session()
        try:
            indexed = 0
            for follower_id in followers:
                self._upsert_feed_entry(
                    session,
                    feed_owner=uuid.UUID(str(follower_id)),
                    content_id=content_id,
                    author_id=author_id,
                    content_type=payload.get("content_type", "post"),
                    policy_scope=payload.get("policy_scope", "default"),
                )
                indexed += 1

            self._upsert_feed_entry(
                session,
                feed_owner=author_id,
                content_id=content_id,
                author_id=author_id,
                content_type=payload.get("content_type", "post"),
                policy_scope=payload.get("policy_scope", "default"),
            )
            indexed += 1

            session.commit()
            return {"status": "indexed", "count": indexed}
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _index_shared_content(self, payload: dict, actor_id) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        sharer_id = uuid.UUID(str(actor_id))
        followers = payload.get("followers", [])

        session = self._get_session()
        try:
            indexed = 0
            for follower_id in followers:
                self._upsert_feed_entry(
                    session,
                    feed_owner=uuid.UUID(str(follower_id)),
                    content_id=content_id,
                    author_id=sharer_id,
                    content_type="shared",
                    policy_scope=payload.get("policy_scope", "default"),
                )
                indexed += 1

            session.commit()
            return {"status": "indexed", "count": indexed}
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _update_reaction_count(self, payload: dict) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        new_count = payload.get("reaction_count", 0)
        feed_owners = payload.get("feed_owners", [])

        session = self._get_session()
        try:
            updated = 0
            for owner_id in feed_owners:
                self._upsert_feed_entry(
                    session,
                    feed_owner=uuid.UUID(str(owner_id)),
                    content_id=content_id,
                    author_id=uuid.UUID(str(payload.get("author_id", "00000000-0000-0000-0000-000000000000"))),
                    reaction_count=new_count,
                )
                updated += 1

            session.commit()
            return {"status": "updated", "count": updated}
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _remove_content(self, payload: dict) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        feed_owners = payload.get("feed_owners", [])

        session = self._get_session()
        try:
            removed = 0
            for owner_id in feed_owners:
                deleted = (
                    session.query(FeedIndex)
                    .filter(
                        FeedIndex.feed_owner == uuid.UUID(str(owner_id)),
                        FeedIndex.content_id == content_id,
                    )
                    .delete()
                )
                if deleted > 0:
                    removed += 1

            session.commit()
            return {"status": "removed", "count": removed}
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()
