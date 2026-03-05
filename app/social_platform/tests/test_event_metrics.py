import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.social_platform.infrastructure.event_metrics import EventMetrics


class TestEventMetrics:
    @patch("app.social_platform.infrastructure.event_metrics.SessionLocal")
    def test_compute_metrics_structure(self, mock_sl):
        mock_session = MagicMock()
        mock_session.execute.return_value = None

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.scalar.return_value = 0
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query

        service = EventMetrics(session=mock_session)
        result = service.compute_metrics(window_seconds=60)

        assert "events_per_second" in result
        assert "events_by_domain" in result
        assert "queue_depth" in result
        assert "retry_rate" in result
        assert "dead_letter_rate" in result
        assert "computed_at" in result

    @patch("app.social_platform.infrastructure.event_metrics.SessionLocal")
    def test_metrics_read_only(self, mock_sl):
        mock_session = MagicMock()
        mock_session.execute.return_value = None

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.scalar.return_value = 0
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query

        service = EventMetrics(session=mock_session)
        service.compute_metrics()

        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    @patch("app.social_platform.infrastructure.event_metrics.SessionLocal")
    def test_events_per_second_calculation(self, mock_sl):
        mock_session = MagicMock()
        mock_session.execute.return_value = None

        call_count = [0]

        def mock_scalar():
            call_count[0] += 1
            if call_count[0] == 1:
                return 120
            return 0

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.scalar.side_effect = mock_scalar
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query

        service = EventMetrics(session=mock_session)
        result = service.compute_metrics(window_seconds=60)

        assert result["events_per_second"] == 2.0
        assert result["recent_events"] == 120

    @patch("app.social_platform.infrastructure.event_metrics.SessionLocal")
    def test_retry_rate_calculation(self, mock_sl):
        mock_session = MagicMock()
        mock_session.execute.return_value = None

        call_count = [0]

        def mock_scalar():
            call_count[0] += 1
            if call_count[0] == 1:
                return 10
            if call_count[0] == 2:
                return 100
            if call_count[0] == 3:
                return 5
            if call_count[0] == 4:
                return 1
            if call_count[0] == 5:
                return 50
            if call_count[0] == 6:
                return 40
            return 0

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.scalar.side_effect = mock_scalar
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query

        service = EventMetrics(session=mock_session)
        result = service.compute_metrics(window_seconds=60)

        assert result["retry_rate"] == round(5 / 100, 4)
        assert result["dead_letter_rate"] == round(1 / 100, 4)
