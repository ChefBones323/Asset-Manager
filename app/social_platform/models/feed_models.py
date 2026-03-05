import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from app.social_platform.models.base import Base


class FeedIndex(Base):
    __tablename__ = "feed_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_owner = Column(UUID(as_uuid=True), nullable=False, index=True)
    content_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content_type = Column(String(50), nullable=False, default="post")
    author_id = Column(UUID(as_uuid=True), nullable=False)
    policy_scope = Column(String(255), nullable=False, default="default")
    reaction_count = Column(Integer, nullable=False, default=0)
    trust_score = Column(Float, nullable=False, default=0.0)
    policy_weight = Column(Float, nullable=False, default=1.0)
    distribution_time = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_feed_owner_dist_time", "feed_owner", "distribution_time"),
        Index("ix_feed_owner_content", "feed_owner", "content_id", unique=True),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "feed_owner": str(self.feed_owner),
            "content_id": str(self.content_id),
            "content_type": self.content_type,
            "author_id": str(self.author_id),
            "policy_scope": self.policy_scope,
            "reaction_count": self.reaction_count,
            "trust_score": self.trust_score,
            "policy_weight": self.policy_weight,
            "distribution_time": self.distribution_time.isoformat() if self.distribution_time else None,
        }
