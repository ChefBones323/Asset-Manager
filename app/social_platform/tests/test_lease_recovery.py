import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.infrastructure.redis_queue import RedisQueue
from app.social_platform.platform.lease_manager import LeaseManager, MAX_RETRY_COUNT


class FakeEvent:
    def __init__(self, event_type, payload, timestamp="2025-01-01T00:00:00+00:00"):
        self.event_type = event_type
        self.payload = payload
        self.timestamp = timestamp
        self.domain = "lease"


class TestLeaseRecovery:
    def _make_manager(self):
        event_store = MagicMock(spec=EventStore)
        event_store.get_events_by_domain.return_value = []
        manager = LeaseManager(event_store)
        return manager, event_store

    def test_record_heartbeat_updates_lease(self):
        manager, es = self._make_manager()
        lease = manager.acquire_lease("job-1", "worker-1")
        assert lease is not None

        result = manager.record_heartbeat("job-1", "worker-1")
        assert result is not None
        assert result["last_heartbeat"] is not None

        hb_calls = [
            c for c in es.append_event.call_args_list
            if c[1].get("event_type") == "heartbeat_received"
        ]
        assert len(hb_calls) == 1

    def test_heartbeat_wrong_worker_returns_none(self):
        manager, _ = self._make_manager()
        manager.acquire_lease("job-1", "worker-1")
        result = manager.record_heartbeat("job-1", "wrong-worker")
        assert result is None

    def test_heartbeat_released_lease_returns_none(self):
        manager, _ = self._make_manager()
        manager.acquire_lease("job-1", "worker-1")
        manager.release_lease("job-1", "worker-1")
        result = manager.record_heartbeat("job-1", "worker-1")
        assert result is None

    def test_detect_stale_leases(self):
        manager, _ = self._make_manager()
        manager.acquire_lease("job-1", "worker-1", lease_timeout=timedelta(seconds=0))
        stale = manager.detect_stale_leases()
        assert len(stale) >= 1
        assert stale[0]["job_id"] == "job-1"

    def test_recover_stale_lease_requeues(self):
        manager, es = self._make_manager()
        manager.acquire_lease("job-1", "worker-1")

        requeue = MagicMock(spec=RedisQueue)
        result = manager.recover_stale_lease("job-1", requeue=requeue)

        assert result["status"] == "requeued"
        assert result["retry_count"] == 1
        requeue.enqueue.assert_called_once()

    def test_recover_exceeds_max_retries_dead_letters(self):
        manager, es = self._make_manager()

        for i in range(MAX_RETRY_COUNT + 1):
            manager.acquire_lease(f"job-dl", f"worker-{i}")
            manager.recover_stale_lease(f"job-dl")

        assert manager.get_retry_count("job-dl") == MAX_RETRY_COUNT + 1

        dl_events = [
            c for c in es.append_event.call_args_list
            if c[1].get("event_type") == "job_dead_lettered"
        ]
        assert len(dl_events) >= 1

    def test_recover_nonexistent_lease(self):
        manager, _ = self._make_manager()
        result = manager.recover_stale_lease("no-such-job")
        assert result["status"] == "not_found"

    def test_lease_has_heartbeat_and_timeout_fields(self):
        manager, _ = self._make_manager()
        lease = manager.acquire_lease("job-hb", "worker-1", lease_timeout=timedelta(seconds=45))
        assert "last_heartbeat" in lease
        assert lease["lease_timeout"] == 45.0

    def test_rebuild_from_event_objects(self):
        event_store = MagicMock(spec=EventStore)
        now = datetime.now(timezone.utc)
        future = (now + timedelta(minutes=5)).isoformat()

        event_store.get_events_by_domain.return_value = [
            FakeEvent(
                event_type="lease_acquired",
                payload={
                    "lease_id": "lease-obj-1",
                    "job_id": "job-obj",
                    "worker_id": "worker-obj",
                    "acquired_at": now.isoformat(),
                    "expires_at": future,
                    "lease_timeout": 30,
                },
                timestamp=now.isoformat(),
            ),
        ]

        manager = LeaseManager(event_store)
        lease = manager._rebuild_from_events("job-obj")
        assert lease is not None
        assert lease["job_id"] == "job-obj"
        assert lease["worker_id"] == "worker-obj"
        assert lease["released"] is False

    def test_rebuild_with_heartbeat_event_objects(self):
        event_store = MagicMock(spec=EventStore)
        now = datetime.now(timezone.utc)
        future = (now + timedelta(minutes=5)).isoformat()
        hb_time = (now + timedelta(seconds=10)).isoformat()

        event_store.get_events_by_domain.return_value = [
            FakeEvent(
                event_type="lease_acquired",
                payload={
                    "lease_id": "lease-hb-1",
                    "job_id": "job-hb-obj",
                    "worker_id": "worker-hb",
                    "acquired_at": now.isoformat(),
                    "expires_at": future,
                    "lease_timeout": 30,
                },
                timestamp=now.isoformat(),
            ),
            FakeEvent(
                event_type="heartbeat_received",
                payload={
                    "job_id": "job-hb-obj",
                    "worker_id": "worker-hb",
                    "timestamp": hb_time,
                },
                timestamp=hb_time,
            ),
        ]

        manager = LeaseManager(event_store)
        lease = manager._rebuild_from_events("job-hb-obj")
        assert lease is not None
        assert lease["last_heartbeat"] == hb_time
