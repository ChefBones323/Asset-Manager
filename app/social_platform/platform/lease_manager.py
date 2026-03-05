import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.infrastructure.redis_queue import RedisQueue

DEFAULT_HEARTBEAT_INTERVAL = 10
DEFAULT_LEASE_TIMEOUT = timedelta(seconds=30)
MAX_RETRY_COUNT = 3


class LeaseManager:
    DEFAULT_LEASE_DURATION = timedelta(minutes=5)

    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._leases: Dict[str, Dict[str, Any]] = {}
        self._retry_counts: Dict[str, int] = {}
        self._dead_letter_queue = RedisQueue("dead_letter")

    def _rebuild_from_events(self, job_id: str) -> Optional[dict]:
        events = self._event_store.get_events_by_domain("lease")

        def _get_payload(event) -> dict:
            if hasattr(event, "payload"):
                return event.payload if isinstance(event.payload, dict) else {}
            if isinstance(event, dict):
                return event.get("payload", {})
            return {}

        def _get_event_type(event) -> str:
            if hasattr(event, "event_type"):
                return event.event_type
            if isinstance(event, dict):
                return event.get("event_type", "")
            return ""

        def _get_timestamp(event):
            if hasattr(event, "timestamp"):
                return event.timestamp
            if isinstance(event, dict):
                return event.get("timestamp", "")
            return ""

        job_events = [e for e in events if _get_payload(e).get("job_id") == job_id]
        job_events.sort(key=lambda e: str(_get_timestamp(e)))

        lease = None
        for event in job_events:
            etype = _get_event_type(event)
            payload = _get_payload(event)
            if etype == "lease_acquired":
                lease = {
                    "lease_id": payload.get("lease_id"),
                    "job_id": payload.get("job_id"),
                    "worker_id": payload.get("worker_id"),
                    "acquired_at": payload.get("acquired_at"),
                    "expires_at": payload.get("expires_at"),
                    "last_heartbeat": payload.get("acquired_at"),
                    "lease_timeout": payload.get("lease_timeout", DEFAULT_LEASE_TIMEOUT.total_seconds()),
                    "released": False,
                }
            elif etype == "lease_released":
                if lease:
                    lease["released"] = True
            elif etype == "lease_renewed":
                if lease:
                    lease["expires_at"] = payload.get("expires_at")
            elif etype == "heartbeat_received":
                if lease:
                    lease["last_heartbeat"] = payload.get("timestamp", lease.get("last_heartbeat"))
        return lease

    def acquire_lease(
        self,
        job_id: str,
        worker_id: str,
        duration: Optional[timedelta] = None,
        lease_timeout: Optional[timedelta] = None,
    ) -> Optional[dict]:
        if duration is None:
            duration = self.DEFAULT_LEASE_DURATION
        if lease_timeout is None:
            lease_timeout = DEFAULT_LEASE_TIMEOUT

        existing = self._leases.get(job_id)
        if not existing:
            existing = self._rebuild_from_events(job_id)

        if existing and not self._is_expired(existing) and not existing.get("released"):
            return None

        now = datetime.now(timezone.utc)
        lease_id = str(uuid.uuid4())
        lease = {
            "lease_id": lease_id,
            "job_id": job_id,
            "worker_id": worker_id,
            "acquired_at": now.isoformat(),
            "expires_at": (now + duration).isoformat(),
            "last_heartbeat": now.isoformat(),
            "lease_timeout": lease_timeout.total_seconds(),
            "released": False,
        }

        self._event_store.append_event(
            domain="lease",
            event_type="lease_acquired",
            actor_id=uuid.UUID(int=0),
            payload=lease,
        )

        self._leases[job_id] = lease
        return lease

    def release_lease(self, job_id: str, worker_id: str) -> bool:
        lease = self._leases.get(job_id)
        if not lease:
            lease = self._rebuild_from_events(job_id)
        if not lease:
            return False
        if lease["worker_id"] != worker_id:
            return False

        lease["released"] = True
        self._leases[job_id] = lease

        self._event_store.append_event(
            domain="lease",
            event_type="lease_released",
            actor_id=uuid.UUID(int=0),
            payload={"job_id": job_id, "worker_id": worker_id, "lease_id": lease["lease_id"]},
        )
        return True

    def record_heartbeat(self, job_id: str, worker_id: str) -> Optional[dict]:
        lease = self._leases.get(job_id)
        if not lease:
            lease = self._rebuild_from_events(job_id)
        if not lease:
            return None
        if lease["worker_id"] != worker_id:
            return None
        if lease["released"]:
            return None

        now = datetime.now(timezone.utc)
        lease["last_heartbeat"] = now.isoformat()
        self._leases[job_id] = lease

        self._event_store.append_event(
            domain="lease",
            event_type="heartbeat_received",
            actor_id=uuid.UUID(int=0),
            payload={
                "job_id": job_id,
                "worker_id": worker_id,
                "lease_id": lease["lease_id"],
                "timestamp": now.isoformat(),
            },
        )
        return lease

    def check_lease(self, job_id: str) -> Optional[dict]:
        lease = self._leases.get(job_id)
        if not lease:
            lease = self._rebuild_from_events(job_id)
        if not lease:
            return None
        if self._is_expired(lease):
            return None
        if lease["released"]:
            return None
        return lease

    def renew_lease(self, job_id: str, worker_id: str, duration: Optional[timedelta] = None) -> Optional[dict]:
        if duration is None:
            duration = self.DEFAULT_LEASE_DURATION

        lease = self._leases.get(job_id)
        if not lease:
            lease = self._rebuild_from_events(job_id)
        if not lease:
            return None
        if lease["worker_id"] != worker_id:
            return None
        if lease["released"]:
            return None
        if self._is_expired(lease):
            return None

        now = datetime.now(timezone.utc)
        new_expires = (now + duration).isoformat()
        lease["expires_at"] = new_expires
        lease["last_heartbeat"] = now.isoformat()
        self._leases[job_id] = lease

        self._event_store.append_event(
            domain="lease",
            event_type="lease_renewed",
            actor_id=uuid.UUID(int=0),
            payload={"job_id": job_id, "worker_id": worker_id, "lease_id": lease["lease_id"], "expires_at": new_expires},
        )
        return lease

    def detect_stale_leases(self) -> List[dict]:
        stale = []
        for job_id, lease in list(self._leases.items()):
            if lease.get("released"):
                continue
            if self._is_heartbeat_stale(lease):
                stale.append(lease)
        return stale

    def recover_stale_lease(self, job_id: str, requeue: Optional[RedisQueue] = None) -> dict:
        lease = self._leases.get(job_id)
        if not lease:
            lease = self._rebuild_from_events(job_id)
        if not lease:
            return {"status": "not_found", "job_id": job_id}

        worker_id = lease["worker_id"]
        lease["released"] = True
        self._leases[job_id] = lease

        self._event_store.append_event(
            domain="lease",
            event_type="lease_recovered",
            actor_id=uuid.UUID(int=0),
            payload={
                "job_id": job_id,
                "worker_id": worker_id,
                "lease_id": lease["lease_id"],
                "reason": "heartbeat_timeout",
            },
        )

        retry_count = self._retry_counts.get(job_id, 0) + 1
        self._retry_counts[job_id] = retry_count

        if retry_count > MAX_RETRY_COUNT:
            self._dead_letter_queue.enqueue({
                "job_id": job_id,
                "reason": "max_retries_exceeded",
                "retry_count": retry_count,
                "last_worker": worker_id,
            })

            self._event_store.append_event(
                domain="lease",
                event_type="job_dead_lettered",
                actor_id=uuid.UUID(int=0),
                payload={
                    "job_id": job_id,
                    "retry_count": retry_count,
                    "reason": "max_retries_exceeded",
                },
            )

            return {
                "status": "dead_lettered",
                "job_id": job_id,
                "retry_count": retry_count,
            }

        if requeue:
            requeue.enqueue({"job_id": job_id, "retry_count": retry_count})

        self._event_store.append_event(
            domain="lease",
            event_type="job_requeued",
            actor_id=uuid.UUID(int=0),
            payload={
                "job_id": job_id,
                "retry_count": retry_count,
            },
        )

        return {
            "status": "requeued",
            "job_id": job_id,
            "retry_count": retry_count,
        }

    def get_retry_count(self, job_id: str) -> int:
        return self._retry_counts.get(job_id, 0)

    def _is_expired(self, lease: dict) -> bool:
        expires_at = datetime.fromisoformat(lease["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at

    def _is_heartbeat_stale(self, lease: dict) -> bool:
        last_hb_str = lease.get("last_heartbeat")
        if not last_hb_str:
            return self._is_expired(lease)
        last_hb = datetime.fromisoformat(last_hb_str)
        if last_hb.tzinfo is None:
            last_hb = last_hb.replace(tzinfo=timezone.utc)
        timeout_seconds = lease.get("lease_timeout", DEFAULT_LEASE_TIMEOUT.total_seconds())
        return (datetime.now(timezone.utc) - last_hb).total_seconds() > timeout_seconds
