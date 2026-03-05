from typing import List, Optional


class PolicyValidationError(Exception):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Policy validation failed: {'; '.join(errors)}")


def validate_policy(policy: dict, existing_ids: Optional[set] = None) -> List[str]:
    errors = []

    policy_id = policy.get("policy_id")
    if not policy_id or not isinstance(policy_id, str) or not policy_id.strip():
        errors.append("policy_id is required and must be a non-empty string")

    if existing_ids and policy_id in existing_ids:
        errors.append(f"policy_id '{policy_id}' already exists; policies must have unique IDs")

    weight_fields = ["timestamp_weight", "reaction_weight", "trust_weight", "policy_weight"]
    weights = []
    for field in weight_fields:
        value = policy.get(field)
        if value is None:
            errors.append(f"{field} is required")
            continue
        if not isinstance(value, (int, float)):
            errors.append(f"{field} must be a number")
            continue
        if value < 0:
            errors.append(f"{field} must be non-negative (got {value})")
        weights.append(value)

    if len(weights) == 4:
        total = sum(weights)
        if abs(total - 1.0) > 0.001:
            errors.append(f"weights must sum to 1.0 (got {total:.4f})")

    max_age = policy.get("max_age_hours")
    if max_age is not None:
        if not isinstance(max_age, (int, float)):
            errors.append("max_age_hours must be a number")
        elif max_age <= 0:
            errors.append(f"max_age_hours must be positive (got {max_age})")

    min_trust = policy.get("min_trust_threshold")
    if min_trust is not None:
        if not isinstance(min_trust, (int, float)):
            errors.append("min_trust_threshold must be a number")

    return errors


def validate_policy_strict(policy: dict, existing_ids: Optional[set] = None) -> dict:
    errors = validate_policy(policy, existing_ids)
    if errors:
        raise PolicyValidationError(errors)
    return policy
