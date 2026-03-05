import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.social_platform.admin.worker_dashboard import _get_worker_data


def _make_lease_event(event_type, job_id, worker_id, timestamp=None, extra_payload=None):
    event = MagicMock()
    event.domain = "lease"
    event.event_type = event_type
    event.timestamp = timestamp or datetime.now(timezone.utc)
    payload = {"job_id": job_id, "worker_id": worker_id}
    if event_type == "lease_acquired":
        payload["lease_id"] = str(uuid.uuid4())
        payload["acquired_at"] = event.timestamp.isoformat()
        payload["expires_at"] = (event.timestamp + timedelta(minutes=5)).isoformat()
    if event_type == "heartbeat_received":
        payload["timestamp"] = event.timestamp.isoformat()
    if event_type == "job_requeued":
        payload["retry_count"] = (extra_payload or {}).get("retry_count", 1)
    if event_type == "job_dead_lettered":
        payload["retry_count"] = (extra_payload or {}).get("retry_count", 4)
        payload["reason"] = "max_retries_exceeded"
    if extra_payload:
        payload.update(extra_payload)
    event.payload = payload
    return event


class TestWorkerDashboard:
    @patch("app.social_platform.admin.worker_dashboard._readonly_session")
    def test_returns_worker_structure(self, mock_session_fn):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None
        mock_session_fn.return_value = mock_session

        data = _get_worker_data()
        assert "workers" in data
        assert "active_leases" in data
        assert "stale_leases" in data
        assert "heartbeats" in data
        assert "retry_counts" in data
        assert "dead_letter_queue" in data
        assert "computed_at" in data

    @patch("app.social_platform.admin.worker_dashboard._readonly_session")
    def test_detects_active_workers(self, mock_session_fn):
        now = datetime.now(timezone.utc)
        events = [
            _make_lease_event("lease_acquired", "job-1", "worker-A", timestamp=now),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None
        mock_session_fn.return_value = mock_session

        data = _get_worker_data()
        assert len(data["workers"]) == 1
        assert data["workers"][0]["worker_id"] == "worker-A"

    @patch("app.social_platform.admin.worker_dashboard._readonly_session")
    def test_detects_dead_letter_entries(self, mock_session_fn):
        now = datetime.now(timezone.utc)
        events = [
            _make_lease_event("job_dead_lettered", "job-2", "worker-B", timestamp=now,
                              extra_payload={"retry_count": 4}),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None
        mock_session_fn.return_value = mock_session

        data = _get_worker_data()
        assert len(data["dead_letter_queue"]) == 1
        assert data["dead_letter_queue"][0]["reason"] == "max_retries_exceeded"

    @patch("app.social_platform.admin.worker_dashboard._readonly_session")
    def test_tracks_heartbeats(self, mock_session_fn):
        now = datetime.now(timezone.utc)
        events = [
            _make_lease_event("lease_acquired", "job-3", "worker-C", timestamp=now),
            _make_lease_event("heartbeat_received", "job-3", "worker-C",
                              timestamp=now + timedelta(seconds=10)),
        ]

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None
        mock_session_fn.return_value = mock_session

        data = _get_worker_data()
        assert len(data["heartbeats"]) == 1
        assert data["heartbeats"][0]["worker_id"] == "worker-C"

    @patch("app.social_platform.admin.worker_dashboard._readonly_session")
    def test_never_mutates(self, mock_session_fn):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_session.execute.return_value = None
        mock_session_fn.return_value = mock_session

        _get_worker_data()
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()
