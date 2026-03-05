import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.social_platform.models.base import Base


class Post(Base):
    __tablename__ = "posts"

    post_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), nullable=False, default="text")
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    parent_post_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    thread_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="published", index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def to_dict(self):
        return {
            "post_id": str(self.post_id),
            "author_id": str(self.author_id),
            "content": self.content,
            "content_type": self.content_type,
            "metadata": self.metadata_,
            "parent_post_id": str(self.parent_post_id) if self.parent_post_id else None,
            "thread_id": str(self.thread_id) if self.thread_id else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Comment(Base):
    __tablename__ = "comments"

    comment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="published")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def to_dict(self):
        return {
            "comment_id": str(self.comment_id),
            "post_id": str(self.post_id),
            "author_id": str(self.author_id),
            "content": self.content,
            "parent_comment_id": str(self.parent_comment_id) if self.parent_comment_id else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Thread(Base):
    __tablename__ = "threads"

    thread_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    root_post_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    participant_count = Column(Integer, nullable=False, default=1)
    reply_count = Column(Integer, nullable=False, default=0)
    last_activity_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "thread_id": str(self.thread_id),
            "root_post_id": str(self.root_post_id),
            "title": self.title,
            "participant_count": self.participant_count,
            "reply_count": self.reply_count,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ReactionSummary(Base):
    __tablename__ = "reaction_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_type = Column(String(50), nullable=False, index=True)
    reaction_type = Column(String(50), nullable=False)
    count = Column(Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            "id": str(self.id),
            "target_id": str(self.target_id),
            "target_type": self.target_type,
            "reaction_type": self.reaction_type,
            "count": self.count,
        }
