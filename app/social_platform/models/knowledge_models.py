import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.social_platform.models.base import Base


class KnowledgeArtifact(Base):
    __tablename__ = "knowledge_artifacts"

    artifact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    artifact_type = Column(String(100), nullable=False, default="article")
    domain = Column(String(255), nullable=False, default="general", index=True)
    knowledge_score = Column(Float, nullable=False, default=0.0)
    citation_count = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="published", index=True)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_knowledge_author_domain", "author_id", "domain"),
    )

    def to_dict(self):
        return {
            "artifact_id": str(self.artifact_id),
            "author_id": str(self.author_id),
            "title": self.title,
            "content": self.content,
            "artifact_type": self.artifact_type,
            "domain": self.domain,
            "knowledge_score": self.knowledge_score,
            "citation_count": self.citation_count,
            "status": self.status,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Citation(Base):
    __tablename__ = "citations"

    citation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_artifact_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    cited_artifact_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    citing_author_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    context = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_citation_source_cited", "source_artifact_id", "cited_artifact_id", unique=True),
    )

    def to_dict(self):
        return {
            "citation_id": str(self.citation_id),
            "source_artifact_id": str(self.source_artifact_id),
            "cited_artifact_id": str(self.cited_artifact_id),
            "citing_author_id": str(self.citing_author_id),
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
