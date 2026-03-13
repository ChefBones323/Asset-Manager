import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from app.social_platform.models.base import SessionLocal

VALID_CATEGORIES = {"profile", "preference", "project", "relationship", "operational", "open_loop"}


class MemoryService:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return SessionLocal()

    def _should_close(self) -> bool:
        return self._session is None

    def store(self, category: str, key: str, value: Any) -> Dict:
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}")

        from app.social_platform.models.agent_memory import AgentMemory
        session = self._get_session()
        try:
            existing = (
                session.query(AgentMemory)
                .filter(AgentMemory.category == category, AgentMemory.key == key)
                .first()
            )
            now = datetime.now(timezone.utc)

            if existing:
                existing.value = value if isinstance(value, str) else str(value)
                existing.updated_at = now
                session.commit()
                session.refresh(existing)
                return existing.to_dict()
            else:
                memory = AgentMemory(
                    id=uuid.uuid4(),
                    category=category,
                    key=key,
                    value=value if isinstance(value, str) else str(value),
                    created_at=now,
                    updated_at=now,
                )
                session.add(memory)
                session.commit()
                session.refresh(memory)
                return memory.to_dict()
        finally:
            if self._should_close():
                session.close()

    def retrieve(self, category: Optional[str] = None, key: Optional[str] = None, limit: int = 50) -> List[Dict]:
        from app.social_platform.models.agent_memory import AgentMemory
        session = self._get_session()
        try:
            query = session.query(AgentMemory)
            if category:
                query = query.filter(AgentMemory.category == category)
            if key:
                query = query.filter(AgentMemory.key == key)
            query = query.order_by(AgentMemory.updated_at.desc()).limit(limit)
            return [m.to_dict() for m in query.all()]
        finally:
            if self._should_close():
                session.close()

    def delete(self, memory_id: str) -> bool:
        from app.social_platform.models.agent_memory import AgentMemory
        session = self._get_session()
        try:
            memory = session.query(AgentMemory).filter(AgentMemory.id == uuid.UUID(memory_id)).first()
            if memory:
                session.delete(memory)
                session.commit()
                return True
            return False
        finally:
            if self._should_close():
                session.close()

    def clear_category(self, category: str) -> int:
        from app.social_platform.models.agent_memory import AgentMemory
        session = self._get_session()
        try:
            count = session.query(AgentMemory).filter(AgentMemory.category == category).delete()
            session.commit()
            return count
        finally:
            if self._should_close():
                session.close()
