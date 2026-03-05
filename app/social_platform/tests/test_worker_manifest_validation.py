import pytest
from unittest.mock import MagicMock

from app.social_platform.infrastructure.worker_runtime import (
    WorkerRuntime,
    WorkerManifest,
    ManifestValidationError,
)


class TestManifestValidation:
    def test_valid_manifest_passes(self):
        runtime = WorkerRuntime()
        manifest = {
            "manifest_id": "abc123",
            "proposal_id": "prop-1",
            "domain": "test",
            "action": "test_action",
            "actor_id": "user-1",
            "payload": {"key": "value"},
            "steps": [
                {"step_id": "s0", "order": 0, "operation": "validate"},
                {"step_id": "s1", "order": 1, "operation": "execute", "params": {}},
            ],
            "checksum": "deadbeef",
        }
        result = runtime.validate_manifest(manifest)
        assert isinstance(result, WorkerManifest)
        assert result.manifest_id == "abc123"

    def test_missing_manifest_id_fails(self):
        runtime = WorkerRuntime()
        manifest = {
            "proposal_id": "prop-1",
            "domain": "test",
            "action": "test_action",
            "actor_id": "user-1",
            "payload": {},
            "steps": [{"step_id": "s0", "order": 0, "operation": "validate"}],
            "checksum": "deadbeef",
        }
        with pytest.raises(ManifestValidationError):
            runtime.validate_manifest(manifest)

    def test_empty_steps_fails(self):
        runtime = WorkerRuntime()
        manifest = {
            "manifest_id": "abc123",
            "proposal_id": "prop-1",
            "domain": "test",
            "action": "test_action",
            "actor_id": "user-1",
            "payload": {},
            "steps": [],
            "checksum": "deadbeef",
        }
        with pytest.raises(ManifestValidationError):
            runtime.validate_manifest(manifest)

    def test_missing_checksum_fails(self):
        runtime = WorkerRuntime()
        manifest = {
            "manifest_id": "abc123",
            "proposal_id": "prop-1",
            "domain": "test",
            "action": "test_action",
            "actor_id": "user-1",
            "payload": {},
            "steps": [{"step_id": "s0", "order": 0, "operation": "validate"}],
        }
        with pytest.raises(ManifestValidationError):
            runtime.validate_manifest(manifest)

    def test_duplicate_step_orders_fails(self):
        runtime = WorkerRuntime()
        manifest = {
            "manifest_id": "abc123",
            "proposal_id": "prop-1",
            "domain": "test",
            "action": "test_action",
            "actor_id": "user-1",
            "payload": {},
            "steps": [
                {"step_id": "s0", "order": 0, "operation": "validate"},
                {"step_id": "s1", "order": 0, "operation": "execute"},
            ],
            "checksum": "deadbeef",
        }
        with pytest.raises(ManifestValidationError):
            runtime.validate_manifest(manifest)

    def test_out_of_order_steps_fails(self):
        runtime = WorkerRuntime()
        manifest = {
            "manifest_id": "abc123",
            "proposal_id": "prop-1",
            "domain": "test",
            "action": "test_action",
            "actor_id": "user-1",
            "payload": {},
            "steps": [
                {"step_id": "s1", "order": 1, "operation": "execute"},
                {"step_id": "s0", "order": 0, "operation": "validate"},
            ],
            "checksum": "deadbeef",
        }
        with pytest.raises(ManifestValidationError):
            runtime.validate_manifest(manifest)

    def test_failed_validation_transitions_job_to_failed(self):
        runtime = WorkerRuntime()
        manifest = {
            "manifest_id": "bad-manifest",
            "proposal_id": "prop-1",
            "domain": "",
            "action": "test",
            "actor_id": "user-1",
            "payload": {},
            "steps": [{"step_id": "s0", "order": 0, "operation": "validate"}],
            "checksum": "deadbeef",
        }
        with pytest.raises(ManifestValidationError):
            runtime.validate_manifest(manifest)
        status = runtime.get_job_status("bad-manifest")
        assert status is not None
        assert status["status"] == "failed"
        assert status["errors"] is not None

    def test_execute_task_validates_manifest_first(self):
        runtime = WorkerRuntime()
        handler = MagicMock(return_value={"done": True})
        runtime.register_worker("w1", handler)

        bad_task = {
            "manifest": {
                "manifest_id": "task-bad",
                "domain": "",
            }
        }
        with pytest.raises(ManifestValidationError):
            runtime.execute_task("w1", bad_task)
        assert handler.call_count == 0
        status = runtime.get_job_status("task-bad")
        assert status["status"] == "failed"

    def test_execute_task_with_valid_manifest_succeeds(self):
        runtime = WorkerRuntime()
        handler = MagicMock(return_value={"result": "ok"})
        runtime.register_worker("w1", handler)

        task = {
            "manifest": {
                "manifest_id": "task-good",
                "proposal_id": "p1",
                "domain": "test",
                "action": "do_it",
                "actor_id": "user-1",
                "payload": {},
                "steps": [{"step_id": "s0", "order": 0, "operation": "validate"}],
                "checksum": "abc",
            }
        }
        result = runtime.execute_task("w1", task)
        assert result == {"result": "ok"}
        assert handler.call_count == 1
        status = runtime.get_job_status("task-good")
        assert status["status"] == "completed"
