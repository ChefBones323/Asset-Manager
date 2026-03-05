import uuid
import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.social_platform.models.event_models import Event, AuditLog
from app.social_platform.models.base import SessionLocal, serializable_session

SERIALIZATION_RETRY_LIMIT = 3
SERIALIZATION_RETRY_BACKOFF = 0.05


class SerializationConflictError(Exception):
    pass


class EventStore:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _get_serializable_session(self) -> Session:
        if self._session:
            return self._session
        return serializable_session()

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
        last_error = None

        for attempt in range(SERIALIZATION_RETRY_LIMIT):
            session = self._get_serializable_session()
            try:
                session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))

                now = datetime.now(timezone.utc)
                event_id = uuid.uuid4()

                event = Event(
                    event_id=event_id,
                    domain=domain,
                    event_type=event_type,
                    actor_id=actor_id,
                    payload=payload,
                    manifest_id=manifest_id,
                    execution_id=execution_id,
                    timestamp=now,
                    signature=signature,
                )

                audit_log = AuditLog(
                    audit_id=uuid.uuid4(),
                    event_id=event_id,
                    domain=domain,
                    event_type=event_type,
                    actor_id=actor_id,
                    resource_type=payload.get("resource_type", domain),
                    resource_id=str(payload.get("resource_id", payload.get("proposal_id", ""))),
                    summary=f"{event_type} by {actor_id}",
                    timestamp=now,
                )

                session.add(event)
                session.add(audit_log)
                session.commit()
                session.refresh(event)
                return event

            except OperationalError as exc:
                session.rollback()
                error_str = str(exc.orig) if hasattr(exc, "orig") else str(exc)
                is_serialization_failure = (
                    "serialization" in error_str.lower()
                    or "could not serialize" in error_str.lower()
                    or "40001" in error_str
                )
                if is_serialization_failure and attempt < SERIALIZATION_RETRY_LIMIT - 1:
                    last_error = exc
                    time.sleep(SERIALIZATION_RETRY_BACKOFF * (attempt + 1))
                    continue
                raise SerializationConflictError(
                    f"Serialization conflict after {attempt + 1} attempts: {error_str}"
                ) from exc

            except Exception:
                session.rollback()
                raise

            finally:
                if self._should_close():
                    session.close()

        raise SerializationConflictError(
            f"Exhausted {SERIALIZATION_RETRY_LIMIT} retries"
        ) from last_error

    def _has_event_sequence(self, session: Session) -> bool:
        try:
            session.execute(text("SELECT event_sequence FROM events LIMIT 0"))
            return True
        except Exception:
            session.rollback()
            return False

    def _apply_ordering(self, query, session: Session):
        if self._has_event_sequence(session):
            return query.order_by(Event.event_sequence.asc())
        return query.order_by(Event.timestamp.asc(), Event.event_id.asc())

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
            query = self._apply_ordering(query, session)
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
            query = session.query(Event).filter(Event.domain == domain)
            query = self._apply_ordering(query, session)
            query = query.offset(offset).limit(limit)
            return query.all()
        finally:
            if self._should_close():
                session.close()

    def get_audit_logs(
        self,
        domain: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        session = self._get_session()
        try:
            query = session.query(AuditLog)
            if domain:
                query = query.filter(AuditLog.domain == domain)
            if actor_id:
                query = query.filter(AuditLog.actor_id == actor_id)
            if resource_id:
                query = query.filter(AuditLog.resource_id == resource_id)
            query = query.order_by(AuditLog.timestamp.desc()).limit(limit)
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
            query = self._apply_ordering(query, session)
            return query.all()
        finally:
            if self._should_close():
                session.close()

    def count_events(self) -> int:
        session = self._get_session()
        try:
            return session.query(Event).count()
        finally:
            if self._should_close():
                session.close()
