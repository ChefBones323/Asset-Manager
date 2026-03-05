from datetime import datetime, timezone
from typing import Optional, List

EPOCH = datetime(2024, 1, 1, tzinfo=timezone.utc)


def compute_feed_score(entry, policy_manifest: Optional[dict] = None) -> float:
    ts_weight = policy_manifest.get("timestamp_weight", 1.0) if policy_manifest else 1.0
    reaction_weight = policy_manifest.get("reaction_weight", 0.1) if policy_manifest else 0.1
    trust_weight = policy_manifest.get("trust_weight", 0.5) if policy_manifest else 0.5
    policy_weight_factor = policy_manifest.get("policy_weight_factor", 1.0) if policy_manifest else 1.0

    dist_time = entry.distribution_time if entry.distribution_time else EPOCH
    time_score = (dist_time - EPOCH).total_seconds() / 86400.0

    return (
        time_score * ts_weight
        + entry.reaction_count * reaction_weight
        + entry.trust_score * trust_weight
        + entry.policy_weight * policy_weight_factor
    )


def deterministic_rank(entries: List, policy_manifest: Optional[dict] = None) -> List:
    return sorted(
        entries,
        key=lambda e: (compute_feed_score(e, policy_manifest), str(e.content_id)),
        reverse=True,
    )


def get_weight_values(policy_manifest: Optional[dict] = None) -> dict:
    return {
        "timestamp_weight": policy_manifest.get("timestamp_weight", 1.0) if policy_manifest else 1.0,
        "reaction_weight": policy_manifest.get("reaction_weight", 0.1) if policy_manifest else 0.1,
        "trust_weight": policy_manifest.get("trust_weight", 0.5) if policy_manifest else 0.5,
        "policy_weight_factor": policy_manifest.get("policy_weight_factor", 1.0) if policy_manifest else 1.0,
    }
