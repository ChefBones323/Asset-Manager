import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.social_platform.models.base import Base

MAX_DELEGATION_DEPTH = 3


class Delegation(Base):
    __tablename__ = "delegations"

    delegation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delegator_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    delegate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    scope = Column(String(255), nullable=False, default="full")
    depth = Column(Integer, nullable=False, default=1)
    max_depth = Column(Integer, nullable=False, default=MAX_DELEGATION_DEPTH)
    is_active = Column(Boolean, nullable=False, default=True)
    reason = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_delegations_active", "delegator_id", "delegate_id", "domain", "is_active"),
        CheckConstraint("depth <= max_depth", name="ck_delegation_depth"),
        CheckConstraint("delegator_id != delegate_id", name="ck_no_self_delegation"),
    )

    def to_dict(self):
        return {
            "delegation_id": str(self.delegation_id),
            "delegator_id": str(self.delegator_id),
            "delegate_id": str(self.delegate_id),
            "domain": self.domain,
            "scope": self.scope,
            "depth": self.depth,
            "max_depth": self.max_depth,
            "is_active": self.is_active,
            "reason": self.reason,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
