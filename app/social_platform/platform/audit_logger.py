import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.social_platform.infrastructure.event_store import EventStore


class AuditLogger:
    def __init__(self, event_store: Optional[EventStore] = None):
        self._event_store = event_store

    def log_action(
        self,
        actor_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[dict] = None,
        outcome: str = "success",
    ) -> dict:
        entry = {
            "audit_id": str(uuid.uuid4()),
            "actor_id": str(actor_id),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self._event_store:
            self._event_store.append_event(
                domain="audit",
                event_type=f"audit_{action}",
                actor_id=actor_id,
                payload=entry,
            )

        return entry

    def get_audit_trail(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> List[dict]:
        if not self._event_store:
            return []

        events = self._event_store.get_events_by_domain("audit")
        results = [e.get("payload", {}) for e in events if e.get("payload")]

        if resource_type:
            results = [e for e in results if e.get("resource_type") == resource_type]
        if resource_id:
            results = [e for e in results if e.get("resource_id") == resource_id]
        if actor_id:
            actor_str = str(actor_id)
            results = [e for e in results if e.get("actor_id") == actor_str]

        results.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return results[:limit]
