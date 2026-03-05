import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from app.social_platform.models.base import SessionLocal
from app.social_platform.models.feed_models import FeedIndex
from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine


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

    def generate_feed(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        policy_manifest: Optional[dict] = None,
    ) -> List[dict]:
        session = self._get_session()
        try:
            entries = (
                session.query(FeedIndex)
                .filter(FeedIndex.feed_owner == user_id)
                .all()
            )

            if policy_manifest:
                self._policy_engine.load_policy_manifest(policy_manifest)

            ranked = self._deterministic_rank(entries, policy_manifest)
            paginated = ranked[offset : offset + limit]
            return [entry.to_dict() for entry in paginated]
        finally:
            if self._should_close():
                session.close()

    def _deterministic_rank(
        self,
        entries: List[FeedIndex],
        policy_manifest: Optional[dict] = None,
    ) -> List[FeedIndex]:
        def compute_score(entry: FeedIndex) -> float:
            ts_weight = policy_manifest.get("timestamp_weight", 1.0) if policy_manifest else 1.0
            reaction_weight = policy_manifest.get("reaction_weight", 0.1) if policy_manifest else 0.1
            trust_weight = policy_manifest.get("trust_weight", 0.5) if policy_manifest else 0.5
            policy_weight_factor = policy_manifest.get("policy_weight_factor", 1.0) if policy_manifest else 1.0

            epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
            dist_time = entry.distribution_time if entry.distribution_time else datetime.now(timezone.utc)
            time_score = (dist_time - epoch).total_seconds() / 86400.0

            score = (
                time_score * ts_weight
                + entry.reaction_count * reaction_weight
                + entry.trust_score * trust_weight
                + entry.policy_weight * policy_weight_factor
            )
            return score

        return sorted(entries, key=lambda e: (compute_score(e), str(e.content_id)), reverse=True)

    def handle_event(self, event) -> dict:
        event_type = event.event_type if hasattr(event, "event_type") else event.get("event_type", "")
        payload = event.payload if hasattr(event, "payload") else event.get("payload", {})

        if event_type == "feed_generate_requested":
            user_id = uuid.UUID(str(payload.get("user_id")))
            limit = payload.get("limit", 50)
            offset = payload.get("offset", 0)
            policy_manifest = payload.get("policy_manifest")
            feed = self.generate_feed(user_id, limit, offset, policy_manifest)
            return {"status": "generated", "count": len(feed), "feed": feed}

        return {"status": "ignored", "event_type": event_type}
