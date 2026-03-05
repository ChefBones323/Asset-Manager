import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.social_platform.workers.feed_generate_worker import FeedGenerateWorker
from app.social_platform.models.feed_models import FeedIndex


class TestFeedRanking:
    def _make_feed_entry(self, **kwargs):
        entry = MagicMock(spec=FeedIndex)
        entry.id = kwargs.get("id", 1)
        entry.feed_owner = kwargs.get("feed_owner", uuid.uuid4())
        entry.content_id = kwargs.get("content_id", uuid.uuid4())
        entry.content_type = kwargs.get("content_type", "post")
        entry.author_id = kwargs.get("author_id", uuid.uuid4())
        entry.policy_scope = kwargs.get("policy_scope", "default")
        entry.reaction_count = kwargs.get("reaction_count", 0)
        entry.trust_score = kwargs.get("trust_score", 0.0)
        entry.policy_weight = kwargs.get("policy_weight", 1.0)
        entry.distribution_time = kwargs.get(
            "distribution_time", datetime.now(timezone.utc)
        )
        entry.to_dict.return_value = {
            "id": entry.id,
            "content_id": str(entry.content_id),
            "reaction_count": entry.reaction_count,
            "trust_score": entry.trust_score,
            "policy_weight": entry.policy_weight,
        }
        return entry

    def test_deterministic_rank_by_time(self):
        worker = FeedGenerateWorker.__new__(FeedGenerateWorker)
        from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
        worker._policy_engine = FeedPolicyEngine()
        worker._session = None

        now = datetime.now(timezone.utc)
        old_entry = self._make_feed_entry(
            distribution_time=now - timedelta(days=10),
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        )
        new_entry = self._make_feed_entry(
            distribution_time=now,
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        )

        ranked = worker._deterministic_rank([old_entry, new_entry])
        assert ranked[0] == new_entry
        assert ranked[1] == old_entry

    def test_deterministic_rank_by_reactions(self):
        worker = FeedGenerateWorker.__new__(FeedGenerateWorker)
        from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
        worker._policy_engine = FeedPolicyEngine()
        worker._session = None

        now = datetime.now(timezone.utc)
        low_reactions = self._make_feed_entry(
            distribution_time=now,
            reaction_count=0,
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        )
        high_reactions = self._make_feed_entry(
            distribution_time=now,
            reaction_count=100,
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        )

        ranked = worker._deterministic_rank([low_reactions, high_reactions])
        assert ranked[0] == high_reactions

    def test_deterministic_rank_with_trust_score(self):
        worker = FeedGenerateWorker.__new__(FeedGenerateWorker)
        from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
        worker._policy_engine = FeedPolicyEngine()
        worker._session = None

        now = datetime.now(timezone.utc)
        low_trust = self._make_feed_entry(
            distribution_time=now,
            trust_score=0.0,
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        )
        high_trust = self._make_feed_entry(
            distribution_time=now,
            trust_score=50.0,
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        )

        ranked = worker._deterministic_rank([low_trust, high_trust])
        assert ranked[0] == high_trust

    def test_deterministic_rank_with_policy_manifest(self):
        worker = FeedGenerateWorker.__new__(FeedGenerateWorker)
        from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
        worker._policy_engine = FeedPolicyEngine()
        worker._session = None

        now = datetime.now(timezone.utc)
        entry_a = self._make_feed_entry(
            distribution_time=now,
            reaction_count=10,
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        )
        entry_b = self._make_feed_entry(
            distribution_time=now,
            reaction_count=5,
            content_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        )

        policy = {"reaction_weight": 10.0, "timestamp_weight": 0.0, "trust_weight": 0.0, "policy_weight_factor": 0.0}
        ranked = worker._deterministic_rank([entry_a, entry_b], policy)
        assert ranked[0] == entry_a

    def test_same_score_uses_content_id_tiebreak(self):
        worker = FeedGenerateWorker.__new__(FeedGenerateWorker)
        from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
        worker._policy_engine = FeedPolicyEngine()
        worker._session = None

        now = datetime.now(timezone.utc)
        id_a = uuid.UUID("00000000-0000-0000-0000-000000000001")
        id_b = uuid.UUID("00000000-0000-0000-0000-000000000002")
        entry_a = self._make_feed_entry(distribution_time=now, content_id=id_a)
        entry_b = self._make_feed_entry(distribution_time=now, content_id=id_b)

        ranked_1 = worker._deterministic_rank([entry_a, entry_b])
        ranked_2 = worker._deterministic_rank([entry_b, entry_a])
        assert str(ranked_1[0].content_id) == str(ranked_2[0].content_id)
