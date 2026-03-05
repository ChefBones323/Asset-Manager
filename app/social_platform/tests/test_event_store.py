import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.models.event_models import Event


class TestEventStore:
    def _make_mock_session(self):
        session = MagicMock()
        return session

    def test_append_event_creates_event(self):
        session = self._make_mock_session()
        store = EventStore(session=session)
        actor_id = uuid.uuid4()

        store.append_event(
            domain="test",
            event_type="test_event",
            actor_id=actor_id,
            payload={"key": "value"},
        )

        session.add.assert_called_once()
        session.commit.assert_called_once()
        added_event = session.add.call_args[0][0]
        assert isinstance(added_event, Event)
        assert added_event.domain == "test"
        assert added_event.event_type == "test_event"
        assert added_event.actor_id == actor_id
        assert added_event.payload == {"key": "value"}

    def test_append_event_rollback_on_error(self):
        session = self._make_mock_session()
        session.commit.side_effect = Exception("DB error")
        store = EventStore(session=session)

        with pytest.raises(Exception, match="DB error"):
            store.append_event(
                domain="test",
                event_type="test_event",
                actor_id=uuid.uuid4(),
                payload={},
            )

        session.rollback.assert_called_once()

    def test_get_events_with_filters(self):
        session = self._make_mock_session()
        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        store = EventStore(session=session)
        after = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = store.get_events(limit=10, offset=0, after=after)

        assert result == []
        session.query.assert_called_once_with(Event)

    def test_get_events_by_domain(self):
        session = self._make_mock_session()
        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        store = EventStore(session=session)
        result = store.get_events_by_domain("content", limit=50)

        assert result == []

    def test_replay_events(self):
        session = self._make_mock_session()
        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        store = EventStore(session=session)
        result = store.replay_events(domain="content")

        assert result == []

    def test_append_event_with_manifest_and_execution(self):
        session = self._make_mock_session()
        store = EventStore(session=session)
        actor_id = uuid.uuid4()
        manifest_id = uuid.uuid4()
        execution_id = uuid.uuid4()

        store.append_event(
            domain="platform",
            event_type="execution_started",
            actor_id=actor_id,
            payload={"test": True},
            manifest_id=manifest_id,
            execution_id=execution_id,
            signature="test_sig",
        )

        added_event = session.add.call_args[0][0]
        assert added_event.manifest_id == manifest_id
        assert added_event.execution_id == execution_id
        assert added_event.signature == "test_sig"
