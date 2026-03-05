import hashlib
import json
from typing import Optional


class ManifestCompiler:
    def compile_manifest(self, proposal: dict) -> dict:
        proposal_id = proposal["proposal_id"]
        manifest_id = self._deterministic_id(proposal_id, "manifest")

        steps = self._derive_steps(proposal)

        manifest = {
            "manifest_id": manifest_id,
            "proposal_id": proposal_id,
            "domain": proposal["domain"],
            "action": proposal["action"],
            "actor_id": proposal["actor_id"],
            "payload": proposal["payload"],
            "steps": steps,
            "checksum": None,
        }

        manifest["checksum"] = self._compute_checksum(manifest)
        return manifest

    def _deterministic_id(self, seed: str, namespace: str) -> str:
        raw = f"{namespace}:{seed}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _derive_steps(self, proposal: dict) -> list:
        action = proposal.get("action", "")
        domain = proposal.get("domain", "")
        proposal_id = proposal["proposal_id"]

        steps = [
            {
                "step_id": self._deterministic_id(proposal_id, "step-0-validate"),
                "order": 0,
                "operation": "validate",
                "description": f"Validate {action} for domain {domain}",
                "params": {},
            },
            {
                "step_id": self._deterministic_id(proposal_id, "step-1-execute"),
                "order": 1,
                "operation": "execute",
                "description": f"Execute {action}",
                "params": proposal.get("payload", {}),
            },
            {
                "step_id": self._deterministic_id(proposal_id, "step-2-emit"),
                "order": 2,
                "operation": "emit_event",
                "description": f"Emit event for {action}",
                "params": {"event_type": action, "domain": domain},
            },
        ]
        return steps

    def _compute_checksum(self, manifest: dict) -> str:
        serializable = {k: v for k, v in manifest.items() if k != "checksum"}
        raw = json.dumps(serializable, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def verify_checksum(self, manifest: dict) -> bool:
        expected = manifest.get("checksum")
        if not expected:
            return False
        return self._compute_checksum(manifest) == expected
