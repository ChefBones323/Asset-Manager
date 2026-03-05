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
        for i, entry in enumerate(filtered_entries):
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

    def compare_policies(
        self,
        policies: List[dict],
        feed_entries: List[dict],
        weights: Optional[dict] = None,
    ) -> dict:
        comparisons = []
        for policy_def in policies:
            result = self.simulate_policy(
                policy_name=policy_def.get("name", "unnamed"),
                rules=policy_def.get("rules", []),
                feed_entries=feed_entries,
                default_weight=policy_def.get("default_weight", 1.0),
                weights=weights,
            )
            comparisons.append({
                "policy_name": policy_def.get("name", "unnamed"),
                "filtered_count": result["filtered_count"],
                "blocked_count": result["blocked_count"],
                "weight_changes_count": len(result["weight_changes"]),
            })

        return {"comparisons": comparisons, "entry_count": len(feed_entries)}
