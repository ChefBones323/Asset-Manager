import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.knowledge_models import KnowledgeArtifact, Citation
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.projection_engine import ProjectionEngine


class KnowledgeWorker:
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
        self._projection_engine.register_handler("artifact_created", self._handle_artifact_created)
        self._projection_engine.register_handler("citation_added", self._handle_citation_added)

    def _handle_artifact_created(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}

            artifact = KnowledgeArtifact(
                artifact_id=uuid.UUID(payload["artifact_id"]),
                author_id=uuid.UUID(payload["author_id"]),
                title=payload.get("title", ""),
                content=payload.get("content", ""),
                artifact_type=payload.get("artifact_type", "article"),
                domain=payload.get("domain", "general"),
                knowledge_score=0.0,
                citation_count=0,
                status="published",
                metadata_=payload.get("metadata", {}),
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(artifact)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _handle_citation_added(self, event: Event):
        session = self._get_session()
        try:
            payload = event.payload or {}

            citation = Citation(
                citation_id=uuid.UUID(payload["citation_id"]),
                source_artifact_id=uuid.UUID(payload["source_artifact_id"]),
                cited_artifact_id=uuid.UUID(payload["cited_artifact_id"]),
                citing_author_id=uuid.UUID(payload["citing_author_id"]),
                context=payload.get("context", ""),
                created_at=event.timestamp or datetime.now(timezone.utc),
            )
            session.add(citation)

            self._recompute_knowledge_score(session, uuid.UUID(payload["cited_artifact_id"]))

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if self._should_close():
                session.close()

    def _recompute_knowledge_score(self, session: Session, artifact_id: uuid.UUID):
        artifact = (
            session.query(KnowledgeArtifact)
            .filter(KnowledgeArtifact.artifact_id == artifact_id)
            .first()
        )
        if not artifact:
            return

        citation_count = (
            session.query(Citation)
            .filter(Citation.cited_artifact_id == artifact_id)
            .count()
        )

        base_score = 1.0
        citation_weight = 2.0
        knowledge_score = base_score + (citation_count * citation_weight)
        knowledge_score = min(100.0, knowledge_score)

        artifact.knowledge_score = knowledge_score
        artifact.citation_count = citation_count
