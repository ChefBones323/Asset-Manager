from typing import Callable, Optional
from app.social_platform.models.event_models import Event
from app.social_platform.infrastructure.event_store import EventStore


class ProjectionEngine:
    def __init__(self, event_store: EventStore):
        self._event_store = event_store
        self._handlers: dict[str, list[Callable[[Event], None]]] = {}

    def register_handler(self, event_type: str, handler: Callable[[Event], None]):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def process_event(self, event: Event):
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            handler(event)

    def rebuild(self, domain: Optional[str] = None):
        events = self._event_store.replay_events(domain=domain)
        for event in events:
            self.process_event(event)

    def process_new_events(self, domain: Optional[str] = None, after=None):
        events = self._event_store.replay_events(domain=domain, after=after)
        for event in events:
            self.process_event(event)
