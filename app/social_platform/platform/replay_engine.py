from typing import Optional, Callable, Dict, List, Any
from datetime import datetime

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.models.event_models import Event


class ReplayEngine:
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._reducers: Dict[str, Callable[[dict, Event], dict]] = {}

    def register_reducer(self, event_type: str, reducer: Callable[[dict, Event], dict]):
        self._reducers[event_type] = reducer

    def replay_from_events(
        self,
        domain: Optional[str] = None,
        since: Optional[datetime] = None,
        initial_state: Optional[dict] = None,
    ) -> dict:
        state = initial_state if initial_state is not None else {}
        events = self._event_store.replay_events(domain=domain, after=since)
        for event in events:
            reducer = self._reducers.get(event.event_type)
            if reducer:
                state = reducer(state, event)
        return state

    def replay_to_list(
        self,
        domain: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[dict]:
        events = self._event_store.replay_events(domain=domain, after=since)
        return [event.to_dict() for event in events]
