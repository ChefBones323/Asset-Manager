import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from app.social_platform.infrastructure.event_store import EventStore


class LeaseManager:
    DEFAULT_LEASE_DURATION = timedelta(minutes=5)

    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._leases: Dict[str, Dict[str, Any]] = {}

    def _rebuild_from_events(self, job_id: str) -> Optional[dict]:
        events = self._event_store.get_events_by_domain("lease")
        job_events = [e for e in events if e.get("payload", {}).get("job_id") == job_id]
        job_events.sort(key=lambda e: e.get("timestamp", ""))

        lease = None
        for event in job_events:
            etype = event.get("event_type", "")
            payload = event.get("payload", {})
            if etype == "lease_acquired":
                lease = {
                    "lease_id": payload.get("lease_id"),
                    "job_id": payload.get("job_id"),
                    "worker_id": payload.get("worker_id"),
                    "acquired_at": payload.get("acquired_at"),
                    "expires_at": payload.get("expires_at"),
                    "released": False,
                }
            elif etype == "lease_released":
                if lease:
                    lease["released"] = True
            elif etype == "lease_renewed":
                if lease:
                    lease["expires_at"] = payload.get("expires_at")
        return lease

    def acquire_lease(
        self,
        job_id: str,
        worker_id: str,
        duration: Optional[timedelta] = None,
    ) -> Optional[dict]:
        if duration is None:
            duration = self.DEFAULT_LEASE_DURATION

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
        self._leases[job_id] = lease

        self._event_store.append_event(
            domain="lease",
            event_type="lease_renewed",
            actor_id=uuid.UUID(int=0),
            payload={"job_id": job_id, "worker_id": worker_id, "lease_id": lease["lease_id"], "expires_at": new_expires},
        )
        return lease

    def _is_expired(self, lease: dict) -> bool:
        expires_at = datetime.fromisoformat(lease["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at
