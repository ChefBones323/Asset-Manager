import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.social_platform.models.base import Base


class TrustEvent(Base):
    __tablename__ = "trust_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    evaluator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    score_delta = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, nullable=True)
    context = Column(JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_trust_events_subject_type", "subject_id", "event_type"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "subject_id": str(self.subject_id),
            "evaluator_id": str(self.evaluator_id),
            "event_type": self.event_type,
            "score_delta": self.score_delta,
            "reason": self.reason,
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TrustProfile(Base):
    __tablename__ = "trust_profiles"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    trust_score = Column(Float, nullable=False, default=0.0)
    positive_events = Column(Integer, nullable=False, default=0)
    negative_events = Column(Integer, nullable=False, default=0)
    total_events = Column(Integer, nullable=False, default=0)
    last_computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "trust_score": self.trust_score,
            "positive_events": self.positive_events,
            "negative_events": self.negative_events,
            "total_events": self.total_events,
            "last_computed_at": self.last_computed_at.isoformat() if self.last_computed_at else None,
        }
