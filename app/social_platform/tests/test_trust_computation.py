import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.social_platform.models.trust_models import TrustEvent, TrustProfile
from app.social_platform.workers.trust_compute_worker import TrustComputeWorker
from app.social_platform.infrastructure.projection_engine import ProjectionEngine
from app.social_platform.infrastructure.event_store import EventStore


class TestTrustComputation:
    def _make_worker(self):
        session = MagicMock()
        event_store = EventStore(session=session)
        projection_engine = ProjectionEngine(event_store)
        worker = TrustComputeWorker(projection_engine, session=session)
        return worker, session

    def _make_trust_event(self, subject_id, score_delta, event_type="endorsement"):
        te = MagicMock(spec=TrustEvent)
        te.subject_id = subject_id
        te.score_delta = score_delta
        te.event_type = event_type
        te.created_at = datetime.now(timezone.utc)
        return te

    def test_recompute_positive_events(self):
        worker, session = self._make_worker()
        user_id = uuid.uuid4()

        events = [
            self._make_trust_event(user_id, 5.0),
            self._make_trust_event(user_id, 3.0),
            self._make_trust_event(user_id, 2.0),
        ]

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_query.first.return_value = None

        worker._recompute_trust_profile(session, user_id)

        session.add.assert_called_once()
        added_profile = session.add.call_args[0][0]
        assert isinstance(added_profile, TrustProfile)
        assert added_profile.trust_score == 10.0
        assert added_profile.positive_events == 3
        assert added_profile.negative_events == 0
        assert added_profile.total_events == 3

    def test_recompute_mixed_events(self):
        worker, session = self._make_worker()
        user_id = uuid.uuid4()

        events = [
            self._make_trust_event(user_id, 10.0),
            self._make_trust_event(user_id, -3.0),
            self._make_trust_event(user_id, 5.0),
            self._make_trust_event(user_id, -7.0),
        ]

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_query.first.return_value = None

        worker._recompute_trust_profile(session, user_id)

        added_profile = session.add.call_args[0][0]
        assert added_profile.trust_score == 5.0
        assert added_profile.positive_events == 2
        assert added_profile.negative_events == 2

    def test_recompute_clamps_to_max(self):
        worker, session = self._make_worker()
        user_id = uuid.uuid4()

        events = [self._make_trust_event(user_id, 200.0)]

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_query.first.return_value = None

        worker._recompute_trust_profile(session, user_id)

        added_profile = session.add.call_args[0][0]
        assert added_profile.trust_score == 100.0

    def test_recompute_clamps_to_min(self):
        worker, session = self._make_worker()
        user_id = uuid.uuid4()

        events = [self._make_trust_event(user_id, -200.0)]

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_query.first.return_value = None

        worker._recompute_trust_profile(session, user_id)

        added_profile = session.add.call_args[0][0]
        assert added_profile.trust_score == -100.0

    def test_recompute_updates_existing_profile(self):
        worker, session = self._make_worker()
        user_id = uuid.uuid4()

        events = [self._make_trust_event(user_id, 10.0)]

        existing_profile = MagicMock(spec=TrustProfile)
        existing_profile.user_id = user_id

        mock_query = MagicMock()
        session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = events
        mock_query.first.return_value = existing_profile

        worker._recompute_trust_profile(session, user_id)

        assert existing_profile.trust_score == 10.0
        assert existing_profile.positive_events == 1
        assert existing_profile.total_events == 1
        session.add.assert_not_called()
