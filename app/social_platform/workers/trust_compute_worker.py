import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.trust_models import TrustEvent, TrustProfile
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine


class TrustComputeWorker:
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
        self._projection_engine.register_handler("trust_event_recorded", self._handle_trust_event)

    def _handle_trust_event(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}
            subject_id = uuid.UUID(payload["subject_id"])
            evaluator_id = uuid.UUID(payload["evaluator_id"])

            trust_event = TrustEvent(
                id=uuid.UUID(payload.get("trust_event_id", str(uuid.uuid4()))),
                subject_id=subject_id,
                evaluator_id=evaluator_id,
                event_type=payload.get("event_type", ""),
                score_delta=payload.get("score_delta", 0.0),
                reason=payload.get("reason", ""),
                context=payload.get("context", {}),
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(trust_event)

            self._recompute_trust_profile(session, subject_id)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _recompute_trust_profile(self, session: Session, user_id: uuid.UUID):
        events = (
            session.query(TrustEvent)
            .filter(TrustEvent.subject_id == user_id)
            .order_by(TrustEvent.created_at.asc())
            .all()
        )

        trust_score = 0.0
        positive_events = 0
        negative_events = 0
        for te in events:
            trust_score += te.score_delta
            if te.score_delta > 0:
                positive_events += 1
            elif te.score_delta < 0:
                negative_events += 1

        trust_score = max(-100.0, min(100.0, trust_score))

        profile = session.query(TrustProfile).filter(TrustProfile.user_id == user_id).first()
        if profile:
            profile.trust_score = trust_score
            profile.positive_events = positive_events
            profile.negative_events = negative_events
            profile.total_events = len(events)
            profile.last_computed_at = datetime.now(timezone.utc)
        else:
            profile = TrustProfile(
                user_id=user_id,
                trust_score=trust_score,
                positive_events=positive_events,
                negative_events=negative_events,
                total_events=len(events),
                last_computed_at=datetime.now(timezone.utc),
            )
            session.add(profile)
