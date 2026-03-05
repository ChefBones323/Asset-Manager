import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.feed_models import FeedIndex
from app.social_platform.domains.social.feed_ranking import (
    compute_feed_score,
    deterministic_rank,
    get_weight_values,
    EPOCH,
)


class FeedExplainService:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_readonly_session(self) -> Session:
        if self._session:
            return self._session
        session = SessionLocal()
        session.execute(text("SET TRANSACTION READ ONLY"))
        return session

    def _should_close(self) -> bool:
        return self._session is None

    def explain(
        self,
        user_id: uuid.UUID,
        content_id: uuid.UUID,
        policy_scope: Optional[str] = None,
        policy_manifest: Optional[dict] = None,
    ) -> dict:
        session = self._get_readonly_session()
        try:
            query = session.query(FeedIndex).filter(FeedIndex.feed_owner == user_id)
            if policy_scope:
                query = query.filter(FeedIndex.policy_scope == policy_scope)
            all_entries = query.all()

            target_entry = None
            for entry in all_entries:
                if entry.content_id == content_id:
                    target_entry = entry
                    break

            if not target_entry:
                return {
                    "content_id": str(content_id),
                    "error": "content_not_found_in_feed",
                    "user_id": str(user_id),
                }

            ranked = deterministic_rank(all_entries, policy_manifest)

            rank_position = -1
            for idx, entry in enumerate(ranked):
                if entry.content_id == content_id:
                    rank_position = idx + 1
                    break

            weights = get_weight_values(policy_manifest)
            ts_weight = weights["timestamp_weight"]
            reaction_weight = weights["reaction_weight"]
            trust_weight = weights["trust_weight"]
            policy_weight_factor = weights["policy_weight_factor"]

            target_dist_time = target_entry.distribution_time if target_entry.distribution_time else EPOCH
            target_time_score = (target_dist_time - EPOCH).total_seconds() / 86400.0

            timestamp_contribution = target_time_score * ts_weight
            reaction_contribution = target_entry.reaction_count * reaction_weight
            trust_contribution = target_entry.trust_score * trust_weight
            policy_contribution = target_entry.policy_weight * policy_weight_factor
            total_score = compute_feed_score(target_entry, policy_manifest)

            score_breakdown = {}
            if total_score > 0:
                score_breakdown = {
                    "timestamp_weight": round(timestamp_contribution / total_score, 4),
                    "reaction_weight": round(reaction_contribution / total_score, 4),
                    "trust_weight": round(trust_contribution / total_score, 4),
                    "policy_weight": round(policy_contribution / total_score, 4),
                }
            else:
                score_breakdown = {
                    "timestamp_weight": 0.0,
                    "reaction_weight": 0.0,
                    "trust_weight": 0.0,
                    "policy_weight": 0.0,
                }

            return {
                "content_id": str(content_id),
                "user_id": str(user_id),
                "rank_position": rank_position,
                "total_entries": len(ranked),
                "final_score": round(total_score, 6),
                "score_breakdown": score_breakdown,
                "score_components": {
                    "timestamp_score": round(timestamp_contribution, 6),
                    "reaction_score": round(reaction_contribution, 6),
                    "trust_score_component": round(trust_contribution, 6),
                    "policy_score": round(policy_contribution, 6),
                },
                "raw_inputs": {
                    "timestamp": target_dist_time.isoformat(),
                    "reaction_count": target_entry.reaction_count,
                    "trust_score": target_entry.trust_score,
                    "policy_weight": target_entry.policy_weight,
                },
                "weights_used": weights,
                "policy_manifest_id": policy_manifest.get("manifest_id") if policy_manifest else None,
                "policy_scope": policy_scope or target_entry.policy_scope,
                "tie_break_rule": "content_id",
            }
        finally:
            if self._should_close():
                session.close()
