import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional


class PolicyCompiler:
    def compile_policy(
        self,
        name: str,
        rules: List[dict],
        default_weight: float = 1.0,
        description: str = "",
        metadata: Optional[dict] = None,
    ) -> dict:
        policy_id = str(uuid.uuid4())
        compiled_rules = []

        for rule in rules:
            compiled_rule = {
                "type": rule.get("type", "boost"),
                "condition": rule.get("condition", {}),
                "factor": rule.get("factor", 1.0),
            }
            compiled_rules.append(compiled_rule)

        policy = {
            "policy_id": policy_id,
            "name": name,
            "description": description,
            "rules": compiled_rules,
            "default_weight": default_weight,
            "metadata": metadata or {},
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "checksum": self._compute_checksum(compiled_rules, default_weight),
        }
        return policy

    def compile_manifest(
        self,
        policies: List[dict],
        manifest_name: str = "feed_policy_manifest",
        weights: Optional[dict] = None,
    ) -> dict:
        manifest_id = str(uuid.uuid4())
        manifest = {
            "manifest_id": manifest_id,
            "name": manifest_name,
            "policies": policies,
            "weights": weights or {
                "timestamp_weight": 1.0,
                "reaction_weight": 0.1,
                "trust_weight": 0.5,
                "policy_weight_factor": 1.0,
            },
            "compiled_at": datetime.now(timezone.utc).isoformat(),
            "checksum": self._compute_manifest_checksum(policies),
        }
        return manifest

    def _compute_checksum(self, rules: List[dict], default_weight: float) -> str:
        data = json.dumps({"rules": rules, "default_weight": default_weight}, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _compute_manifest_checksum(self, policies: List[dict]) -> str:
        checksums = [p.get("checksum", "") for p in policies]
        data = json.dumps(sorted(checksums))
        return hashlib.sha256(data.encode()).hexdigest()[:16]
