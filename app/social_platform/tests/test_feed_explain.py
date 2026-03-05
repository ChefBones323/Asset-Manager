import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.social_platform.domains.social.feed_explain_service import FeedExplainService


def _make_feed_entry(content_id, reaction_count=0, trust_score=0.0, policy_weight=1.0,
                     distribution_time=None, feed_owner=None, policy_scope="default"):
    entry = MagicMock()
    entry.content_id = content_id
    entry.feed_owner = feed_owner or uuid.uuid4()
    entry.reaction_count = reaction_count
    entry.trust_score = trust_score
    entry.policy_weight = policy_weight
    entry.distribution_time = distribution_time or datetime(2024, 6, 15, tzinfo=timezone.utc)
    entry.policy_scope = policy_scope
    return entry


class TestFeedExplainService:
    def test_explain_returns_rank_position(self):
        user_id = uuid.uuid4()
        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()
        cid3 = uuid.uuid4()

        entries = [
            _make_feed_entry(cid1, reaction_count=10, trust_score=0.9,
                             distribution_time=datetime(2024, 7, 1, tzinfo=timezone.utc), feed_owner=user_id),
            _make_feed_entry(cid2, reaction_count=5, trust_score=0.5,
                             distribution_time=datetime(2024, 6, 15, tzinfo=timezone.utc), feed_owner=user_id),
            _make_feed_entry(cid3, reaction_count=2, trust_score=0.3,
                             distribution_time=datetime(2024, 6, 1, tzinfo=timezone.utc), feed_owner=user_id),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = entries
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        service = FeedExplainService(session=mock_session)
        result = service.explain(user_id, cid2)

        assert result["content_id"] == str(cid2)
        assert result["rank_position"] > 0
        assert result["total_entries"] == 3
        assert result["tie_break_rule"] == "content_id"

    def test_explain_score_breakdown_sums_to_one(self):
        user_id = uuid.uuid4()
        cid = uuid.uuid4()

        entries = [
            _make_feed_entry(cid, reaction_count=10, trust_score=0.8, policy_weight=1.5,
                             distribution_time=datetime(2024, 7, 1, tzinfo=timezone.utc), feed_owner=user_id),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = entries
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        service = FeedExplainService(session=mock_session)
        result = service.explain(user_id, cid)

        bd = result["score_breakdown"]
        total = bd["timestamp_weight"] + bd["reaction_weight"] + bd["trust_weight"] + bd["policy_weight"]
        assert abs(total - 1.0) < 0.01

    def test_explain_content_not_found(self):
        user_id = uuid.uuid4()
        cid = uuid.uuid4()

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        service = FeedExplainService(session=mock_session)
        result = service.explain(user_id, cid)

        assert result["error"] == "content_not_found_in_feed"

    def test_explain_uses_same_ranking_as_feed_generate(self):
        user_id = uuid.uuid4()
        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()

        t1 = datetime(2024, 8, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)

        entries = [
            _make_feed_entry(cid1, reaction_count=0, trust_score=0.0,
                             distribution_time=t1, feed_owner=user_id),
            _make_feed_entry(cid2, reaction_count=0, trust_score=0.0,
                             distribution_time=t2, feed_owner=user_id),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = entries
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        service = FeedExplainService(session=mock_session)
        result = service.explain(user_id, cid1)

        assert result["rank_position"] == 1

    def test_explain_with_policy_manifest(self):
        user_id = uuid.uuid4()
        cid = uuid.uuid4()

        entries = [
            _make_feed_entry(cid, reaction_count=5, trust_score=0.5,
                             distribution_time=datetime(2024, 7, 1, tzinfo=timezone.utc), feed_owner=user_id),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = entries
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        manifest = {
            "manifest_id": "test-manifest-1",
            "timestamp_weight": 0.4,
            "reaction_weight": 0.25,
            "trust_weight": 0.2,
            "policy_weight_factor": 0.15,
        }

        service = FeedExplainService(session=mock_session)
        result = service.explain(user_id, cid, policy_manifest=manifest)

        assert result["policy_manifest_id"] == "test-manifest-1"
        assert result["weights_used"]["timestamp_weight"] == 0.4

    def test_explain_never_mutates(self):
        user_id = uuid.uuid4()
        cid = uuid.uuid4()

        entries = [
            _make_feed_entry(cid, reaction_count=5, trust_score=0.5,
                             distribution_time=datetime(2024, 7, 1, tzinfo=timezone.utc), feed_owner=user_id),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = entries
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None

        service = FeedExplainService(session=mock_session)
        service.explain(user_id, cid)

        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
