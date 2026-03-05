import uuid
from datetime import datetime, timezone, timedelta

from app.social_platform.policies.policy_simulator import PolicySimulator


class TestPolicySimulator:
    def _make_entries(self, count=5):
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        entries = []
        for i in range(count):
            entries.append({
                "content_id": str(uuid.uuid4()),
                "content_type": "post",
                "author_id": str(uuid.uuid4()),
                "policy_scope": "default",
                "reaction_count": i * 3,
                "trust_score": 50.0 + i * 5,
                "policy_weight": 1.0,
                "distribution_time": (base_time + timedelta(hours=i)).isoformat(),
            })
        return entries

    def test_simulate_ranking_is_dry_run(self):
        sim = PolicySimulator()
        entries = self._make_entries()

        result = sim.simulate_ranking(
            policy_name="test_boost",
            rules=[{"type": "boost", "condition": {"content_type": "post"}, "factor": 2.0}],
            feed_entries=entries,
        )

        assert result["is_dry_run"] is True
        assert "ranked_results" in result
        assert "position_changes" in result
        assert "weights_used" in result

    def test_simulate_ranking_computes_scores(self):
        sim = PolicySimulator()
        entries = self._make_entries(3)

        result = sim.simulate_ranking(
            policy_name="test",
            rules=[],
            feed_entries=entries,
        )

        for item in result["ranked_results"]:
            assert "computed_score" in item
            assert isinstance(item["computed_score"], float)

    def test_simulate_ranking_does_not_modify_input(self):
        sim = PolicySimulator()
        entries = self._make_entries(3)
        original_entries = [dict(e) for e in entries]

        sim.simulate_ranking(
            policy_name="test",
            rules=[{"type": "boost", "condition": {"content_type": "post"}, "factor": 5.0}],
            feed_entries=entries,
        )

        for orig, current in zip(original_entries, entries):
            assert orig == current

    def test_simulate_ranking_with_block_rule(self):
        sim = PolicySimulator()
        entries = self._make_entries(3)
        entries[1]["content_type"] = "spam"

        result = sim.simulate_ranking(
            policy_name="block_spam",
            rules=[{"type": "block", "condition": {"content_type": "spam"}}],
            feed_entries=entries,
        )

        assert result["simulation"]["blocked_count"] == 1
        result_ids = [e["content_id"] for e in result["ranked_results"]]
        assert entries[1]["content_id"] not in result_ids

    def test_compare_policies_dry_run(self):
        sim = PolicySimulator()
        entries = self._make_entries(4)

        result = sim.compare_policies(
            policies=[
                {"name": "policy_a", "rules": [{"type": "boost", "condition": {"content_type": "post"}, "factor": 2.0}]},
                {"name": "policy_b", "rules": [{"type": "demote", "condition": {"content_type": "post"}, "factor": 0.3}]},
            ],
            feed_entries=entries,
        )

        assert result["is_dry_run"] is True
        assert len(result["comparisons"]) == 2
        assert result["comparisons"][0]["policy_name"] == "policy_a"
        assert result["comparisons"][1]["policy_name"] == "policy_b"

    def test_simulate_ranking_respects_custom_weights(self):
        sim = PolicySimulator()
        entries = self._make_entries(3)

        custom_weights = {
            "timestamp_weight": 0.0,
            "reaction_weight": 10.0,
            "trust_weight": 0.0,
            "policy_weight_factor": 0.0,
        }

        result = sim.simulate_ranking(
            policy_name="reaction_heavy",
            rules=[],
            feed_entries=entries,
            weights=custom_weights,
        )

        assert result["weights_used"] == custom_weights
        scores = [e["computed_score"] for e in result["ranked_results"]]
        assert scores == sorted(scores, reverse=True)
