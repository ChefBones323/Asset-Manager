import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.delegation_models import Delegation
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine


class DelegationWorker:
    def __init__(self, projection_engine: ProjectionEngine, session: Optional[Session] = None):
        self._projection_engine = projection_engine
        self._session = session
        self._register_handlers()

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def _register_handlers(self):
        self._projection_engine.register_handler("delegation_created", self._handle_delegation_created)
        self._projection_engine.register_handler("delegation_revoked", self._handle_delegation_revoked)

    def _handle_delegation_created(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}

            delegation = Delegation(
                delegation_id=uuid.UUID(payload["delegation_id"]),
                delegator_id=uuid.UUID(payload["delegator_id"]),
                delegate_id=uuid.UUID(payload["delegate_id"]),
                domain=payload.get("domain", ""),
                scope=payload.get("scope", "full"),
                depth=payload.get("depth", 1),
                is_active=True,
                reason=payload.get("reason", ""),
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(delegation)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_delegation_revoked(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            delegation_id = uuid.UUID(payload["delegation_id"])

            delegation = (
                session.query(Delegation)
                .filter(Delegation.delegation_id == delegation_id)
                .first()
            )
            if delegation:
                delegation.is_active = False
                delegation.revoked_at = event.timestamp or datetime.now(timezone.utc)
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()
