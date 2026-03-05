import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.social_platform.models.base import Base


class GovernanceProposal(Base):
    __tablename__ = "governance_proposals"

    proposal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    proposal_type = Column(String(100), nullable=False, default="policy_change")
    domain = Column(String(255), nullable=False, default="general", index=True)
    payload = Column(JSONB, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="open", index=True)
    quorum = Column(Integer, nullable=False, default=1)
    approval_threshold = Column(Float, nullable=False, default=0.5)
    votes_for = Column(Integer, nullable=False, default=0)
    votes_against = Column(Integer, nullable=False, default=0)
    total_votes = Column(Integer, nullable=False, default=0)
    execution_result = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_gov_proposals_status_domain", "status", "domain"),
    )

    def to_dict(self):
        return {
            "proposal_id": str(self.proposal_id),
            "author_id": str(self.author_id),
            "title": self.title,
            "description": self.description,
            "proposal_type": self.proposal_type,
            "domain": self.domain,
            "payload": self.payload,
            "status": self.status,
            "quorum": self.quorum,
            "approval_threshold": self.approval_threshold,
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "total_votes": self.total_votes,
            "execution_result": self.execution_result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class GovernanceVote(Base):
    __tablename__ = "governance_votes"

    vote_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    proposal_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    voter_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    vote = Column(String(20), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_gov_votes_proposal_voter", "proposal_id", "voter_id", unique=True),
    )

    def to_dict(self):
        return {
            "vote_id": str(self.vote_id),
            "proposal_id": str(self.proposal_id),
            "voter_id": str(self.voter_id),
            "vote": self.vote,
            "weight": self.weight,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
