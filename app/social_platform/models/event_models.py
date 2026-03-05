import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.social_platform.models.base import Base


class Event(Base):
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(255), nullable=False, index=True)
    event_type = Column(String(255), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    payload = Column(JSONB, nullable=False, default=dict)
    manifest_id = Column(UUID(as_uuid=True), nullable=True)
    execution_id = Column(UUID(as_uuid=True), nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    signature = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "event_id": str(self.event_id),
            "domain": self.domain,
            "event_type": self.event_type,
            "actor_id": str(self.actor_id),
            "payload": self.payload,
            "manifest_id": str(self.manifest_id) if self.manifest_id else None,
            "execution_id": str(self.execution_id) if self.execution_id else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "signature": self.signature,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    event_type = Column(String(255), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    resource_type = Column(String(255), nullable=True)
    resource_id = Column(String(255), nullable=True, index=True)
    summary = Column(Text, nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "audit_id": str(self.audit_id),
            "event_id": str(self.event_id),
            "domain": self.domain,
            "event_type": self.event_type,
            "actor_id": str(self.actor_id),
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
