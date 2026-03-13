from typing import Dict, Any, List, Optional

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.agent_runtime.memory_service import MemoryService


class RuntimeContext:
    def __init__(
        self,
        user_input: str,
        event_store: EventStore,
        memory_service: MemoryService,
    ):
        self.user_input = user_input
        self.plan: List[str] = []
        self.tool_calls: List[Dict[str, Any]] = []
        self.results: List[Dict[str, Any]] = []
        self.completed = False
        self.error: Optional[str] = None
        self.iteration = 0
        self._event_store = event_store
        self._memory_service = memory_service

    def build(self) -> Dict[str, Any]:
        recent_events = self._get_recent_events()
        memories = self._get_relevant_memories()
        system_snapshot = self._get_system_snapshot()

        return {
            "user_input": self.user_input,
            "recent_events": recent_events,
            "memories": memories,
            "system_snapshot": system_snapshot,
            "plan": self.plan,
            "tool_calls": self.tool_calls,
            "results": self.results,
            "iteration": self.iteration,
        }

    def _get_recent_events(self, limit: int = 20) -> List[Dict]:
        try:
            events = self._event_store.get_events(limit=limit)
            return [e.to_dict() for e in events]
        except Exception:
            return []

    def _get_relevant_memories(self) -> List[Dict]:
        try:
            return self._memory_service.retrieve(limit=10)
        except Exception:
            return []

    def _get_system_snapshot(self) -> Dict[str, Any]:
        try:
            total_events = self._event_store.count_events()
            return {"total_events": total_events, "status": "operational"}
        except Exception:
            return {"total_events": 0, "status": "unknown"}

    def update(self, tool_call: Dict, result: Dict) -> None:
        self.tool_calls.append(tool_call)
        self.results.append(result)
        self.iteration += 1

    def mark_complete(self) -> None:
        self.completed = True

    def mark_error(self, error: str) -> None:
        self.error = error
        self.completed = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_input": self.user_input,
            "plan": self.plan,
            "tool_calls": self.tool_calls,
            "results": self.results,
            "completed": self.completed,
            "error": self.error,
            "iteration": self.iteration,
        }
