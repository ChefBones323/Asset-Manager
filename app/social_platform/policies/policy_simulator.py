from datetime import datetime, timezone
from typing import List, Optional
from app.social_platform.policies.policy_compiler import PolicyCompiler
from app.social_platform.policies.policy_executor import PolicyExecutor


class PolicySimulator:
    def __init__(self):
        self._compiler = PolicyCompiler()
        self._executor = PolicyExecutor()

    def simulate_policy(
        self,
        policy_name: str,
        rules: List[dict],
        feed_entries: List[dict],
        default_weight: float = 1.0,
        weights: Optional[dict] = None,
    ) -> dict:
        policy = self._compiler.compile_policy(
            name=policy_name,
            rules=rules,
            default_weight=default_weight,
        )

        manifest = self._compiler.compile_manifest(
            policies=[policy],
            manifest_name=f"simulation_{policy_name}",
            weights=weights,
        )

        filtered_entries = self._executor.execute_policy(manifest, feed_entries)

        original_count = len(feed_entries)
        filtered_count = len(filtered_entries)
        blocked_count = original_count - filtered_count

        weight_changes = []
        for entry in filtered_entries:
            original_idx = next(
                (j for j, e in enumerate(feed_entries) if e.get("content_id") == entry.get("content_id")),
                -1,
            )
            if original_idx >= 0:
                original_weight = feed_entries[original_idx].get("policy_weight", 1.0)
                new_weight = entry.get("policy_weight", 1.0)
                if abs(original_weight - new_weight) > 0.001:
                    weight_changes.append({
                        "content_id": entry.get("content_id"),
                        "original_weight": original_weight,
                        "new_weight": new_weight,
                    })

        return {
            "policy": policy,
            "manifest": manifest,
            "original_count": original_count,
            "filtered_count": filtered_count,
            "blocked_count": blocked_count,
            "weight_changes": weight_changes,
            "results": filtered_entries,
        }

    def simulate_ranking(
        self,
        policy_name: str,
        rules: List[dict],
        feed_entries: List[dict],
        default_weight: float = 1.0,
        weights: Optional[dict] = None,
    ) -> dict:
        simulation = self.simulate_policy(
            policy_name=policy_name,
            rules=rules,
            feed_entries=feed_entries,
            default_weight=default_weight,
            weights=weights,
        )

        effective_weights = weights or {
            "timestamp_weight": 1.0,
            "reaction_weight": 0.1,
            "trust_weight": 0.5,
            "policy_weight_factor": 1.0,
        }

        epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
        ranked = []
        for entry in simulation["results"]:
            dist_time_str = entry.get("distribution_time")
            if dist_time_str and isinstance(dist_time_str, str):
                dist_time = datetime.fromisoformat(dist_time_str)
            elif isinstance(dist_time_str, datetime):
                dist_time = dist_time_str
            else:
                dist_time = datetime.now(timezone.utc)

            time_score = (dist_time - epoch).total_seconds() / 86400.0
            score = (
                time_score * effective_weights.get("timestamp_weight", 1.0)
                + entry.get("reaction_count", 0) * effective_weights.get("reaction_weight", 0.1)
                + entry.get("trust_score", 0.0) * effective_weights.get("trust_weight", 0.5)
                + entry.get("policy_weight", 1.0) * effective_weights.get("policy_weight_factor", 1.0)
            )
            ranked.append({
                **entry,
                "computed_score": round(score, 6),
            })

        ranked.sort(key=lambda e: (e["computed_score"], str(e.get("content_id", ""))), reverse=True)

        original_order = [e.get("content_id") for e in feed_entries]
        new_order = [e.get("content_id") for e in ranked]
        position_changes = []
        for content_id in new_order:
            old_pos = original_order.index(content_id) if content_id in original_order else -1
            new_pos = new_order.index(content_id)
            if old_pos != new_pos:
                position_changes.append({
                    "content_id": content_id,
                    "old_position": old_pos,
                    "new_position": new_pos,
                    "delta": old_pos - new_pos,
                })

        return {
            "simulation": simulation,
            "ranked_results": ranked,
            "position_changes": position_changes,
            "weights_used": effective_weights,
            "is_dry_run": True,
        }

    def compare_policies(
        self,
        policies: List[dict],
        feed_entries: List[dict],
        weights: Optional[dict] = None,
    ) -> dict:
        comparisons = []
        for policy_def in policies:
            result = self.simulate_ranking(
                policy_name=policy_def.get("name", "unnamed"),
                rules=policy_def.get("rules", []),
                feed_entries=feed_entries,
                default_weight=policy_def.get("default_weight", 1.0),
                weights=weights,
            )
            comparisons.append({
                "policy_name": policy_def.get("name", "unnamed"),
                "filtered_count": result["simulation"]["filtered_count"],
                "blocked_count": result["simulation"]["blocked_count"],
                "weight_changes_count": len(result["simulation"]["weight_changes"]),
                "position_changes_count": len(result["position_changes"]),
                "top_5": [
                    {"content_id": e.get("content_id"), "score": e.get("computed_score")}
                    for e in result["ranked_results"][:5]
                ],
            })

        return {
            "comparisons": comparisons,
            "entry_count": len(feed_entries),
            "is_dry_run": True,
        }
