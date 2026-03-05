import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.social_platform.models.event_models import Event
from app.social_platform.models.base import SessionLocal


class EventStore:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def append_event(
        self,
        domain: str,
        event_type: str,
        actor_id: uuid.UUID,
        payload: dict,
        manifest_id: Optional[uuid.UUID] = None,
        execution_id: Optional[uuid.UUID] = None,
        signature: Optional[str] = None,
    ) -> Event:
        session = self._get_session()
        try:
            event = Event(
                event_id=uuid.uuid4(),
                domain=domain,
                event_type=event_type,
                actor_id=actor_id,
                payload=payload,
                manifest_id=manifest_id,
                execution_id=execution_id,
                timestamp=datetime.now(timezone.utc),
                signature=signature,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
    ) -> list[Event]:
        session = self._get_session()
        try:
            query = session.query(Event)
            if after:
                query = query.filter(Event.timestamp > after)
            if before:
                query = query.filter(Event.timestamp < before)
            query = query.order_by(Event.timestamp.asc())
            query = query.offset(offset).limit(limit)
            return query.all()
        finally:
            if self._should_close():
                session.close()

    def get_events_by_domain(
        self,
        domain: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Event]:
        session = self._get_session()
        try:
            query = (
                session.query(Event)
                .filter(Event.domain == domain)
                .order_by(Event.timestamp.asc())
                .offset(offset)
                .limit(limit)
            )
            return query.all()
        finally:
            if self._should_close():
                session.close()

    def replay_events(
        self,
        domain: Optional[str] = None,
        after: Optional[datetime] = None,
    ) -> list[Event]:
        session = self._get_session()
        try:
            query = session.query(Event)
            if domain:
                query = query.filter(Event.domain == domain)
            if after:
                query = query.filter(Event.timestamp > after)
            query = query.order_by(Event.timestamp.asc())
            return query.all()
        finally:
            if self._should_close():
                session.close()
