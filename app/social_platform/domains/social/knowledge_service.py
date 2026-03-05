import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.social_platform.models.base import SessionLocal
from app.social_platform.models.knowledge_models import KnowledgeArtifact, Citation
from app.social_platform.platform.execution_engine import ExecutionEngine


class KnowledgeService:
    DOMAIN = "knowledge"

    def __init__(self, execution_engine: ExecutionEngine, session: Optional[Session] = None):
        self._engine = execution_engine
        self._session = session
        self._engine.register_executor("create_artifact", self._execute_create_artifact)
        self._engine.register_executor("add_citation", self._execute_add_citation)

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def create_artifact(
        self,
        actor_id: uuid.UUID,
        title: str,
        content: str,
        artifact_type: str = "article",
        domain: str = "general",
        metadata: Optional[dict] = None,
    ) -> dict:
        payload = {
            "title": title,
            "content": content,
            "artifact_type": artifact_type,
            "domain": domain,
            "metadata": metadata or {},
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="create_artifact",
            payload=payload,
            description=f"Create {artifact_type}: {title[:50]}",
        )

    def add_citation(
        self,
        actor_id: uuid.UUID,
        source_artifact_id: uuid.UUID,
        cited_artifact_id: uuid.UUID,
        context: str = "",
    ) -> dict:
        payload = {
            "source_artifact_id": str(source_artifact_id),
            "cited_artifact_id": str(cited_artifact_id),
            "context": context,
        }
        return self._engine.submit_proposal(
            actor_id=actor_id,
            domain=self.DOMAIN,
            action="add_citation",
            payload=payload,
            description=f"Cite artifact {cited_artifact_id}",
        )

    def compute_knowledge_score(self, artifact_id: uuid.UUID) -> dict:
        session = self._get_session()
        try:
            artifact = (
                session.query(KnowledgeArtifact)
                .filter(KnowledgeArtifact.artifact_id == artifact_id)
                .first()
            )
            if not artifact:
                return {"artifact_id": str(artifact_id), "knowledge_score": 0.0, "citation_count": 0}

            citation_count = (
                session.query(Citation)
                .filter(Citation.cited_artifact_id == artifact_id)
                .count()
            )

            base_score = 1.0
            citation_weight = 2.0
            knowledge_score = base_score + (citation_count * citation_weight)
            knowledge_score = min(100.0, knowledge_score)

            return {
                "artifact_id": str(artifact_id),
                "title": artifact.title if hasattr(artifact, "title") else "",
                "knowledge_score": knowledge_score,
                "citation_count": citation_count,
                "stored_score": artifact.knowledge_score if hasattr(artifact, "knowledge_score") else None,
            }
        finally:
            if self._should_close():
                session.close()

    def get_artifact(self, artifact_id: uuid.UUID) -> Optional[dict]:
        session = self._get_session()
        try:
            artifact = (
                session.query(KnowledgeArtifact)
                .filter(KnowledgeArtifact.artifact_id == artifact_id)
                .first()
            )
            return artifact.to_dict() if artifact else None
        finally:
            if self._should_close():
                session.close()

    def _execute_create_artifact(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))
        artifact_id = uuid.uuid4()

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="artifact_created",
            actor_id=actor_id,
            payload={
                "artifact_id": str(artifact_id),
                "author_id": str(actor_id),
                "title": payload.get("title", ""),
                "content": payload.get("content", ""),
                "artifact_type": payload.get("artifact_type", "article"),
                "domain": payload.get("domain", "general"),
                "metadata": payload.get("metadata", {}),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"artifact_id": str(artifact_id), "status": "created"}

    def _execute_add_citation(self, manifest: dict) -> dict:
        payload = manifest.get("payload", {})
        actor_id = uuid.UUID(manifest.get("actor_id", manifest.get("proposal", {}).get("actor_id", "")))
        citation_id = uuid.uuid4()

        self._engine._event_store.append_event(
            domain=self.DOMAIN,
            event_type="citation_added",
            actor_id=actor_id,
            payload={
                "citation_id": str(citation_id),
                "source_artifact_id": payload.get("source_artifact_id"),
                "cited_artifact_id": payload.get("cited_artifact_id"),
                "citing_author_id": str(actor_id),
                "context": payload.get("context", ""),
            },
            manifest_id=uuid.UUID(manifest.get("manifest_id", str(uuid.uuid4()))),
        )
        return {"citation_id": str(citation_id), "status": "cited"}
