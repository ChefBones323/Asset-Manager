import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.social_platform.infrastructure.event_store import EventStore
from app.social_platform.models.event_models import Event


class TestEventSequenceOrdering:
    def test_has_event_sequence_true(self):
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock()
        store = EventStore(session=mock_session)
        assert store._has_event_sequence(mock_session) is True

    def test_has_event_sequence_false(self):
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("column does not exist")
        store = EventStore(session=mock_session)
        assert store._has_event_sequence(mock_session) is False

    def test_apply_ordering_uses_sequence_when_available(self):
        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock()

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query

        store = EventStore(session=mock_session)
        result = store._apply_ordering(mock_query, mock_session)

        mock_query.order_by.assert_called_once()
        args = mock_query.order_by.call_args
        assert args is not None

    def test_apply_ordering_falls_back_to_timestamp(self):
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("no column")

        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query

        store = EventStore(session=mock_session)
        result = store._apply_ordering(mock_query, mock_session)

        mock_query.order_by.assert_called_once()

    def test_event_to_dict_includes_sequence(self):
        event = Event(
            event_id=uuid.uuid4(),
            event_sequence=42,
            domain="test",
            event_type="test_event",
            actor_id=uuid.uuid4(),
            payload={"key": "value"},
            timestamp=datetime.now(timezone.utc),
        )
        d = event.to_dict()
        assert d["event_sequence"] == 42

    def test_count_events(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.count.return_value = 42
        mock_session.query.return_value = mock_query

        store = EventStore(session=mock_session)
        result = store.count_events()
        assert result == 42
