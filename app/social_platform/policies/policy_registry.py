from typing import Optional, List, Dict
from datetime import datetime, timezone

from app.social_platform.policies.feed_policy_manifest import FeedPolicyManifest, SYSTEM_DEFAULT_POLICY
from app.social_platform.policies.policy_validator import validate_policy_strict, PolicyValidationError


class PolicyAlreadyPublishedError(Exception):
    pass


class PolicyNotFoundError(Exception):
    pass


class PolicyRegistry:
    def __init__(self):
        self._policies: Dict[str, dict] = {}
        self._approval_status: Dict[str, str] = {}
        self._register_default()

    def _register_default(self):
        default = SYSTEM_DEFAULT_POLICY.to_dict()
        default["status"] = "active"
        default["approved"] = True
        self._policies["system_default"] = default
        self._approval_status["system_default"] = "approved"

    def register_policy(self, policy_manifest: dict, approved: bool = False) -> dict:
        policy_id = policy_manifest.get("policy_id")

        if policy_id in self._policies:
            existing = self._policies[policy_id]
            if existing.get("status") == "active":
                raise PolicyAlreadyPublishedError(
                    f"Policy '{policy_id}' is already published and immutable"
                )

        existing_ids = set(self._policies.keys()) - {policy_id}
        validate_policy_strict(policy_manifest, existing_ids)

        manifest = FeedPolicyManifest.from_dict(policy_manifest)
        entry = manifest.to_dict()
        entry["status"] = "active" if approved else "pending_approval"
        entry["approved"] = approved
        entry["registered_at"] = datetime.now(timezone.utc).isoformat()

        self._policies[policy_id] = entry
        self._approval_status[policy_id] = "approved" if approved else "pending"
        return entry

    def approve_policy(self, policy_id: str) -> dict:
        if policy_id not in self._policies:
            raise PolicyNotFoundError(f"Policy '{policy_id}' not found")

        entry = self._policies[policy_id]
        entry["status"] = "active"
        entry["approved"] = True
        entry["approved_at"] = datetime.now(timezone.utc).isoformat()
        self._approval_status[policy_id] = "approved"
        return entry

    def get_policy(self, policy_id: str) -> Optional[dict]:
        return self._policies.get(policy_id)

    def get_active_policy(self, policy_id: str) -> Optional[dict]:
        entry = self._policies.get(policy_id)
        if entry and entry.get("status") == "active" and entry.get("approved"):
            return entry
        return None

    def list_policies(self) -> List[dict]:
        return list(self._policies.values())

    def list_active_policies(self) -> List[dict]:
        return [p for p in self._policies.values() if p.get("status") == "active" and p.get("approved")]

    def get_approval_status(self, policy_id: str) -> Optional[str]:
        return self._approval_status.get(policy_id)

    def resolve_policy(self, community_id: Optional[str] = None, organization_id: Optional[str] = None) -> dict:
        if community_id:
            policy = self.get_active_policy(f"community_{community_id}")
            if policy:
                return policy

        if organization_id:
            policy = self.get_active_policy(f"org_{organization_id}")
            if policy:
                return policy

        return self._policies["system_default"]


_global_registry = PolicyRegistry()


def get_global_registry() -> PolicyRegistry:
    return _global_registry
