from typing import List, Optional
from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine


class PolicyExecutor:
    def __init__(self):
        self._engine = FeedPolicyEngine()

    def execute_policy(
        self,
        manifest: dict,
        feed_entries: List[dict],
    ) -> List[dict]:
        self._engine.load_policy_manifest(manifest)
        policies = self._engine.list_policies()

        results = []
        for entry in feed_entries:
            context = {
                "content_type": entry.get("content_type", "post"),
                "author_id": entry.get("author_id", ""),
                "policy_scope": entry.get("policy_scope", "default"),
                "reaction_count": entry.get("reaction_count", 0),
                "trust_score": entry.get("trust_score", 0.0),
            }

            combined_weight = entry.get("policy_weight", 1.0)
            allowed = True

            for policy in policies:
                policy_id = policy.get("policy_id", policy.get("name", ""))
                evaluation = self._engine.evaluate_policy(policy_id, context)
                if not evaluation["allowed"]:
                    allowed = False
                    break
                combined_weight *= evaluation["weight"]

            if allowed:
                modified_entry = dict(entry)
                modified_entry["policy_weight"] = combined_weight
                results.append(modified_entry)

        return results

    def execute_single(self, manifest: dict, entry: dict) -> Optional[dict]:
        result = self.execute_policy(manifest, [entry])
        return result[0] if result else None
