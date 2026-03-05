import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.social_platform.models.base import SessionLocal
from app.social_platform.models.feed_models import FeedIndex
from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
from app.social_platform.domains.social.feed_ranking import deterministic_rank
from app.social_platform.policies.policy_registry import get_global_registry


class FeedGenerateWorker:
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._policy_engine = FeedPolicyEngine()

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def _resolve_policy_manifest(
        self,
        policy_manifest: Optional[dict] = None,
        community_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> Optional[dict]:
        if policy_manifest:
            return policy_manifest

        registry = get_global_registry()
        policy_entry = registry.resolve_policy(
            community_id=community_id,
            organization_id=organization_id,
        )

        if policy_entry:
            from app.social_platform.policies.feed_policy_manifest import FeedPolicyManifest
            manifest = FeedPolicyManifest.from_dict(policy_entry)
            return manifest.to_ranking_manifest()

        return None

    def generate_feed(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        policy_manifest: Optional[dict] = None,
        community_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> List[dict]:
        session = self._get_session()
        try:
            entries = (
                session.query(FeedIndex)
                .filter(FeedIndex.feed_owner == user_id)
                .all()
            )

            resolved_manifest = self._resolve_policy_manifest(
                policy_manifest, community_id, organization_id
            )

            if resolved_manifest:
                self._policy_engine.load_policy_manifest(resolved_manifest)

            ranked = deterministic_rank(entries, resolved_manifest)
            paginated = ranked[offset : offset + limit]
            return [entry.to_dict() for entry in paginated]
        finally:
            if self._should_close():
                session.close()

    def handle_event(self, event) -> dict:
        event_type = event.event_type if hasattr(event, "event_type") else event.get("event_type", "")
        payload = event.payload if hasattr(event, "payload") else event.get("payload", {})

        if event_type == "feed_generate_requested":
            user_id = uuid.UUID(str(payload.get("user_id")))
            limit = payload.get("limit", 50)
            offset = payload.get("offset", 0)
            policy_manifest = payload.get("policy_manifest")
            community_id = payload.get("community_id")
            organization_id = payload.get("organization_id")
            feed = self.generate_feed(
                user_id, limit, offset, policy_manifest,
                community_id=community_id,
                organization_id=organization_id,
            )
            return {"status": "generated", "count": len(feed), "feed": feed}

        return {"status": "ignored", "event_type": event_type}
