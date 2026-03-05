import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.event_models import Event


class EventMetrics:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_readonly_session(self) -> Session:
        if self._session:
            return self._session
        session = SessionLocal()
        session.execute(text("SET TRANSACTION READ ONLY"))
        return session

    def _should_close(self) -> bool:
        return self._session is None

    def compute_metrics(self, window_seconds: int = 60) -> dict:
        session = self._get_readonly_session()
        try:
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(seconds=window_seconds)

            recent_count = (
                session.query(func.count(Event.event_id))
                .filter(Event.timestamp >= window_start)
                .scalar()
            ) or 0

            events_per_second = round(recent_count / window_seconds, 2) if window_seconds > 0 else 0.0

            domain_rows = (
                session.query(Event.domain, func.count(Event.event_id))
                .filter(Event.timestamp >= window_start)
                .group_by(Event.domain)
                .all()
            )
            events_by_domain = {row[0]: row[1] for row in domain_rows}

            total_events = (
                session.query(func.count(Event.event_id)).scalar()
            ) or 0

            retry_events = (
                session.query(func.count(Event.event_id))
                .filter(Event.event_type == "job_requeued")
                .scalar()
            ) or 0

            dead_letter_events = (
                session.query(func.count(Event.event_id))
                .filter(Event.event_type == "job_dead_lettered")
                .scalar()
            ) or 0

            queue_depth = (
                session.query(func.count(Event.event_id))
                .filter(
                    Event.domain == "lease",
                    Event.event_type == "lease_acquired",
                )
                .scalar()
            ) or 0

            released = (
                session.query(func.count(Event.event_id))
                .filter(
                    Event.domain == "lease",
                    Event.event_type.in_(["lease_released", "lease_recovered"]),
                )
                .scalar()
            ) or 0

            active_queue = max(0, queue_depth - released)

            retry_rate = round(retry_events / total_events, 4) if total_events > 0 else 0.0
            dead_letter_rate = round(dead_letter_events / total_events, 4) if total_events > 0 else 0.0

            type_rows = (
                session.query(Event.event_type, func.count(Event.event_id))
                .filter(Event.timestamp >= window_start)
                .group_by(Event.event_type)
                .all()
            )
            events_by_type = {row[0]: row[1] for row in type_rows}

            return {
                "events_per_second": events_per_second,
                "events_by_domain": events_by_domain,
                "events_by_type": events_by_type,
                "total_events": total_events,
                "recent_events": recent_count,
                "window_seconds": window_seconds,
                "queue_depth": active_queue,
                "retry_count": retry_events,
                "retry_rate": retry_rate,
                "dead_letter_count": dead_letter_events,
                "dead_letter_rate": dead_letter_rate,
                "computed_at": now.isoformat(),
            }
        finally:
            if self._should_close():
                session.close()
