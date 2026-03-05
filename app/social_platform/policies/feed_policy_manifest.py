import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional


class FeedPolicyManifest:
    def __init__(
        self,
        policy_id: str,
        timestamp_weight: float = 0.40,
        reaction_weight: float = 0.25,
        trust_weight: float = 0.20,
        policy_weight: float = 0.15,
        max_age_hours: int = 72,
        min_trust_threshold: float = -20.0,
        description: str = "",
        created_by: Optional[str] = None,
    ):
        self.policy_id = policy_id
        self.timestamp_weight = timestamp_weight
        self.reaction_weight = reaction_weight
        self.trust_weight = trust_weight
        self.policy_weight = policy_weight
        self.max_age_hours = max_age_hours
        self.min_trust_threshold = min_trust_threshold
        self.description = description
        self.created_by = created_by
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.version = self._compute_version()

    def _compute_version(self) -> str:
        canonical = json.dumps({
            "policy_id": self.policy_id,
            "timestamp_weight": self.timestamp_weight,
            "reaction_weight": self.reaction_weight,
            "trust_weight": self.trust_weight,
            "policy_weight": self.policy_weight,
            "max_age_hours": self.max_age_hours,
            "min_trust_threshold": self.min_trust_threshold,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "timestamp_weight": self.timestamp_weight,
            "reaction_weight": self.reaction_weight,
            "trust_weight": self.trust_weight,
            "policy_weight": self.policy_weight,
            "max_age_hours": self.max_age_hours,
            "min_trust_threshold": self.min_trust_threshold,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "version": self.version,
        }

    def to_ranking_manifest(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "timestamp_weight": self.timestamp_weight,
            "reaction_weight": self.reaction_weight,
            "trust_weight": self.trust_weight,
            "policy_weight_factor": self.policy_weight,
            "max_age_hours": self.max_age_hours,
            "min_trust_threshold": self.min_trust_threshold,
            "manifest_id": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedPolicyManifest":
        manifest = cls(
            policy_id=data["policy_id"],
            timestamp_weight=data.get("timestamp_weight", 0.40),
            reaction_weight=data.get("reaction_weight", 0.25),
            trust_weight=data.get("trust_weight", 0.20),
            policy_weight=data.get("policy_weight", 0.15),
            max_age_hours=data.get("max_age_hours", 72),
            min_trust_threshold=data.get("min_trust_threshold", -20.0),
            description=data.get("description", ""),
            created_by=data.get("created_by"),
        )
        if "created_at" in data:
            manifest.created_at = data["created_at"]
        return manifest


SYSTEM_DEFAULT_POLICY = FeedPolicyManifest(
    policy_id="system_default",
    timestamp_weight=1.0,
    reaction_weight=0.1,
    trust_weight=0.5,
    policy_weight=1.0,
    max_age_hours=168,
    min_trust_threshold=-100.0,
    description="System default feed policy with original ranking weights",
)
