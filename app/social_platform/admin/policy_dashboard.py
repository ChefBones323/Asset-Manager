from typing import Optional, List

from app.social_platform.policies.feed_policy_engine import FeedPolicyEngine
from app.social_platform.policies.policy_simulator import PolicySimulator


class PolicyDashboard:
    def __init__(self):
        self._policy_engine = FeedPolicyEngine()
        self._simulator = PolicySimulator()

    def get_overview(self) -> dict:
        manifest = self._policy_engine.get_manifest()
        policies = self._policy_engine.list_policies()
        return {
            "has_manifest": manifest is not None,
            "policy_count": len(policies),
            "policies": policies,
        }

    def load_manifest(self, manifest: dict) -> dict:
        self._policy_engine.load_policy_manifest(manifest)
        return {"status": "loaded", "policy_count": len(self._policy_engine.list_policies())}

    def evaluate_policy(self, policy_id: str, context: dict) -> dict:
        return self._policy_engine.evaluate_policy(policy_id, context)

    def simulate(
        self,
        policy_name: str,
        rules: list,
        feed_entries: list,
        default_weight: float = 1.0,
        weights: Optional[dict] = None,
    ) -> dict:
        return self._simulator.simulate_policy(
            policy_name=policy_name,
            rules=rules,
            feed_entries=feed_entries,
            default_weight=default_weight,
            weights=weights,
        )

    def list_policies(self) -> List[dict]:
        return self._policy_engine.list_policies()
