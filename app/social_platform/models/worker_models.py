import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.social_platform.models.base import Base


class WorkerNode(Base):
    __tablename__ = "worker_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="idle")
    capabilities = Column(JSON, nullable=False, default=list)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    current_job_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        now = datetime.now(timezone.utc)
        hb = self.last_heartbeat
        heartbeat_age = None
        if hb:
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)
            heartbeat_age = (now - hb).total_seconds()
        return {
            "id": str(self.id),
            "hostname": self.hostname,
            "status": self.status,
            "capabilities": self.capabilities or [],
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "heartbeat_age_seconds": round(heartbeat_age, 1) if heartbeat_age is not None else None,
            "current_job_id": str(self.current_job_id) if self.current_job_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JobQueueEntry(Base):
    __tablename__ = "job_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id = Column(String(255), nullable=False)
    tool_name = Column(String(255), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="queued")
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    claimed_by_worker = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "proposal_id": self.proposal_id,
            "tool_name": self.tool_name,
            "payload": self.payload,
            "status": self.status,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "claimed_by_worker": str(self.claimed_by_worker) if self.claimed_by_worker else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DeadLetterEntry(Base):
    __tablename__ = "dead_letter_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), nullable=False)
    error_message = Column(Text, nullable=False, default="")
    failed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "job_id": str(self.job_id),
            "error_message": self.error_message,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
        }
