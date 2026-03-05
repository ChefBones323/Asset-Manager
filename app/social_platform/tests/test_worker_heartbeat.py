import uuid
import time
from unittest.mock import MagicMock

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.infrastructure.worker_runtime import (
    WorkerRuntime,
    ManifestValidationError,
)
from app.social_platform.platform.lease_manager import LeaseManager


class TestWorkerHeartbeat:
    def _make_runtime(self):
        event_store = MagicMock(spec=EventStore)
        event_store.get_events_by_domain.return_value = []
        lease_manager = MagicMock(spec=LeaseManager)
        lease_manager.record_heartbeat.return_value = {"job_id": "test", "last_heartbeat": "now"}
        runtime = WorkerRuntime(
            event_store=event_store,
            lease_manager=lease_manager,
            heartbeat_interval=0.1,
        )
        return runtime, event_store, lease_manager

    def test_heartbeat_started_during_task(self):
        runtime, es, lm = self._make_runtime()

        def slow_handler(task):
            time.sleep(0.3)
            return {"done": True}

        runtime.register_worker("w1", slow_handler)
        runtime._running = True

        task = {
            "job_id": "job-hb-test",
            "manifest": {
                "manifest_id": "m1",
                "proposal_id": "p1",
                "domain": "test",
                "action": "do_it",
                "actor_id": "user-1",
                "payload": {},
                "steps": [{"step_id": "s0", "order": 0, "operation": "validate"}],
                "checksum": "abc",
            },
        }
        runtime.execute_task("w1", task)

        assert lm.record_heartbeat.call_count >= 1

    def test_heartbeat_stops_after_task(self):
        runtime, es, lm = self._make_runtime()

        def fast_handler(task):
            return {"done": True}

        runtime.register_worker("w1", fast_handler)
        runtime._running = True

        task = {
            "job_id": "job-fast",
            "manifest": {
                "manifest_id": "m2",
                "proposal_id": "p2",
                "domain": "test",
                "action": "do_it",
                "actor_id": "user-1",
                "payload": {},
                "steps": [{"step_id": "s0", "order": 0, "operation": "validate"}],
                "checksum": "abc",
            },
        }
        runtime.execute_task("w1", task)

        key = "w1:job-fast"
        assert key not in runtime._heartbeat_threads

    def test_manifest_failure_writes_audit_record(self):
        runtime, es, lm = self._make_runtime()
        runtime.register_worker("w1", MagicMock())

        bad_manifest = {"manifest_id": "bad-m", "domain": ""}

        try:
            runtime.validate_manifest(bad_manifest)
        except ManifestValidationError:
            pass

        audit_calls = [
            c for c in es.append_event.call_args_list
            if c[1].get("domain") == "audit"
            and "validation_failed" in c[1].get("event_type", "")
        ]
        assert len(audit_calls) >= 1

    def test_execution_failure_writes_audit_record(self):
        runtime, es, lm = self._make_runtime()

        def failing_handler(task):
            raise RuntimeError("worker crashed")

        runtime.register_worker("w1", failing_handler)
        runtime._running = True

        task = {
            "job_id": "job-fail",
            "manifest": {
                "manifest_id": "m-fail",
                "proposal_id": "p1",
                "domain": "test",
                "action": "do_it",
                "actor_id": "user-1",
                "payload": {},
                "steps": [{"step_id": "s0", "order": 0, "operation": "validate"}],
                "checksum": "abc",
            },
        }

        try:
            runtime.execute_task("w1", task)
        except RuntimeError:
            pass

        audit_calls = [
            c for c in es.append_event.call_args_list
            if c[1].get("domain") == "audit"
            and "execution_failed" in c[1].get("event_type", "")
        ]
        assert len(audit_calls) >= 1
