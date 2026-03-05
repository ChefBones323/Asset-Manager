import unittest
from unittest.mock import patch, MagicMock
import uuid
import json
from datetime import datetime, timezone

from app.social_platform.admin.event_stream_inspector import (
    _query_events,
    _count_events,
    _format_sse,
    _readonly_session,
)


class TestEventStreamInspector(unittest.TestCase):

    def test_format_sse_event(self):
        data = {"event_id": "abc", "domain": "content"}
        result = _format_sse(data, "event")
        self.assertTrue(result.startswith("event: event\n"))
        self.assertIn("data: ", result)
        self.assertTrue(result.endswith("\n\n"))
        parsed = json.loads(result.split("data: ")[1].strip())
        self.assertEqual(parsed["event_id"], "abc")
        self.assertEqual(parsed["domain"], "content")

    def test_format_sse_control(self):
        data = {"status": "connected"}
        result = _format_sse(data, "control")
        self.assertIn("event: control", result)
        parsed = json.loads(result.split("data: ")[1].strip())
        self.assertEqual(parsed["status"], "connected")

    def test_format_sse_batch(self):
        data = {"type": "batch", "count": 3, "events": [{"id": 1}, {"id": 2}, {"id": 3}]}
        result = _format_sse(data, "batch")
        self.assertIn("event: batch", result)

    def test_query_events_applies_domain_filter(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = _query_events(mock_session, domain="content", limit=10, offset=0)
        self.assertEqual(result, [])
        mock_query.filter.assert_called_once()

    def test_query_events_applies_multiple_filters(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        actor = uuid.uuid4()
        result = _query_events(
            mock_session,
            domain="trust",
            actor_id=actor,
            event_type="trust_event_recorded",
            limit=5,
            offset=0,
        )
        self.assertEqual(result, [])
        self.assertEqual(mock_query.filter.call_count, 3)

    def test_query_events_no_filters(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = _query_events(mock_session, limit=50, offset=0)
        self.assertEqual(result, [])
        mock_query.filter.assert_not_called()

    def test_count_events_with_domain(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 42

        result = _count_events(mock_session, domain="content")
        self.assertEqual(result, 42)

    def test_count_events_no_filter(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.count.return_value = 100

        result = _count_events(mock_session)
        self.assertEqual(result, 100)
        mock_query.filter.assert_not_called()

    @patch("app.social_platform.admin.event_stream_inspector.SessionLocal")
    def test_readonly_session_sets_read_only(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value = mock_session

        session = _readonly_session()
        mock_session.execute.assert_called_once()
        from sqlalchemy import text
        arg = mock_session.execute.call_args[0][0]
        self.assertIn("READ ONLY", arg.text)

    def test_query_events_applies_after_timestamp(self):
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
        result = _query_events(mock_session, after_timestamp=ts, limit=10, offset=0)
        self.assertEqual(result, [])
        mock_query.filter.assert_called_once()


if __name__ == "__main__":
    unittest.main()
