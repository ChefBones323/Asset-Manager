import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.social_platform.models.base import SessionLocal
from app.social_platform.domains.social.feed_service import FeedService


class FeedIndexWorker:
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._feed_service = FeedService(session)

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

    def _index_new_content(self, payload: dict, actor_id) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        author_id = uuid.UUID(str(actor_id))
        followers = payload.get("followers", [])

        indexed = 0
        for follower_id in followers:
            self._feed_service.index_content(
                feed_owner=uuid.UUID(str(follower_id)),
                content_id=content_id,
                author_id=author_id,
                content_type=payload.get("content_type", "post"),
                policy_scope=payload.get("policy_scope", "default"),
            )
            indexed += 1

        self._feed_service.index_content(
            feed_owner=author_id,
            content_id=content_id,
            author_id=author_id,
            content_type=payload.get("content_type", "post"),
            policy_scope=payload.get("policy_scope", "default"),
        )
        indexed += 1

        return {"status": "indexed", "count": indexed}

    def _index_shared_content(self, payload: dict, actor_id) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        sharer_id = uuid.UUID(str(actor_id))
        followers = payload.get("followers", [])

        indexed = 0
        for follower_id in followers:
            self._feed_service.index_content(
                feed_owner=uuid.UUID(str(follower_id)),
                content_id=content_id,
                author_id=sharer_id,
                content_type="shared",
                policy_scope=payload.get("policy_scope", "default"),
            )
            indexed += 1

        return {"status": "indexed", "count": indexed}

    def _update_reaction_count(self, payload: dict) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        new_count = payload.get("reaction_count", 0)
        feed_owners = payload.get("feed_owners", [])

        updated = 0
        for owner_id in feed_owners:
            self._feed_service.index_content(
                feed_owner=uuid.UUID(str(owner_id)),
                content_id=content_id,
                author_id=uuid.UUID(str(payload.get("author_id", "00000000-0000-0000-0000-000000000000"))),
                reaction_count=new_count,
            )
            updated += 1

        return {"status": "updated", "count": updated}

    def _remove_content(self, payload: dict) -> dict:
        content_id = uuid.UUID(str(payload.get("content_id", payload.get("post_id", ""))))
        feed_owners = payload.get("feed_owners", [])

        removed = 0
        for owner_id in feed_owners:
            if self._feed_service.remove_content(
                feed_owner=uuid.UUID(str(owner_id)),
                content_id=content_id,
            ):
                removed += 1

        return {"status": "removed", "count": removed}
