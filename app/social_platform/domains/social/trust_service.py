import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.trust_models import TrustEvent, TrustProfile
from app.social_platform.platform.execution_engine import ExecutionEngine


class TrustService:
    DOMAIN = "trust"

    def __init__(self, execution_engine: ExecutionEngine, session: Optional[Session] = None):
        self._engine = execution_engine
        self._session = session
        self._engine.register_executor("record_trust_event", self._execute_record_trust_event)

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def record_trust_event(
        self,
        actor_id: uuid.UUID,
        subject_id: uuid.UUID,
        event_type: str,
        score_delta: float,
        reason: str = "",
        context: Optional[dict] = None,
    ) -> dict:
        payload = {
            "subject_id": str(subject_id),
            "event_type": event_type,
            "score_delta": score_delta,
            "reason": reason,
            "context": context or {},
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="record_trust_event",
            payload=payload,
            description=f"Trust event ({event_type}) for {subject_id}",
        )

    def get_trust_profile(self, user_id: uuid.UUID) -> Optional[dict]:
        session = self._get_session()
        try:
            profile = session.query(TrustProfile).filter(TrustProfile.user_id == user_id).first()
            if profile:
                return profile.to_dict()
            return None
        finally:
            if self._should_close():
                session.close()

    def compute_trust(self, user_id: uuid.UUID) -> dict:
        session = self._get_session()
        try:
            events = (
                session.query(TrustEvent)
                .filter(TrustEvent.subject_id == user_id)
                .order_by(TrustEvent.created_at.asc())
                .all()
            )

            trust_score = 0.0
            positive_events = 0
            negative_events = 0
            for event in events:
                trust_score += event.score_delta
                if event.score_delta > 0:
                    positive_events += 1
                elif event.score_delta < 0:
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

            session.commit()
            session.refresh(profile)
            return profile.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _execute_record_trust_event(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))
        trust_event_id = uuid.uuid4()

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="trust_event_recorded",
            actor_id=actor_id,
            payload={
                "trust_event_id": str(trust_event_id),
                "subject_id": payload.get("subject_id"),
                "event_type": payload.get("event_type"),
                "score_delta": payload.get("score_delta", 0.0),
                "reason": payload.get("reason", ""),
                "context": payload.get("context", {}),
                "evaluator_id": str(actor_id),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"trust_event_id": str(trust_event_id), "status": "recorded"}
