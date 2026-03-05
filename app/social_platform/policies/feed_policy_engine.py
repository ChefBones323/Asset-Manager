from typing import Optional, Dict, Any, List


class FeedPolicyEngine:
    def __init__(self):
        self._manifest: Optional[dict] = None
        self._policies: Dict[str, dict] = {}

    def load_policy_manifest(self, manifest: dict):
        self._manifest = manifest
        policies = manifest.get("policies", [])
        for policy in policies:
            policy_id = policy.get("policy_id", policy.get("name", ""))
            self._policies[policy_id] = policy

    def evaluate_policy(
        self,
        policy_id: str,
        context: dict,
    ) -> dict:
        policy = self._policies.get(policy_id)
        if not policy:
            return {"allowed": True, "weight": 1.0, "reason": "no_policy_found"}

        rules = policy.get("rules", [])
        weight = policy.get("default_weight", 1.0)
        allowed = True

        for rule in rules:
            rule_type = rule.get("type", "")
            if rule_type == "block":
                if self._matches_condition(rule.get("condition", {}), context):
                    allowed = False
                    weight = 0.0
                    break
            elif rule_type == "boost":
                if self._matches_condition(rule.get("condition", {}), context):
                    weight *= rule.get("factor", 1.5)
            elif rule_type == "demote":
                if self._matches_condition(rule.get("condition", {}), context):
                    weight *= rule.get("factor", 0.5)

        return {"allowed": allowed, "weight": weight, "policy_id": policy_id}

    def _matches_condition(self, condition: dict, context: dict) -> bool:
        for key, expected in condition.items():
            actual = context.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    def get_manifest(self) -> Optional[dict]:
        return self._manifest

    def list_policies(self) -> List[dict]:
        return list(self._policies.values())
