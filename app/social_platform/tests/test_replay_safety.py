from unittest.mock import MagicMock, patch

from app.social_platform.tools.replay_social_system import run_replay, check_active_workers


class TestReplaySafetyLock:
    @patch("app.social_platform.tools.replay_social_system.check_active_workers")
    @patch("app.social_platform.tools.replay_social_system.SessionLocal")
    @patch("app.social_platform.tools.replay_social_system.EventStore")
    @patch("app.social_platform.tools.replay_social_system.ProjectionEngine")
    def test_aborts_when_workers_active_without_force(self, mock_pe_cls, mock_es_cls, mock_session_cls, mock_check):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        mock_session.execute.return_value = result_mock

        mock_es = MagicMock()
        mock_es_cls.return_value = mock_es
        mock_pe = MagicMock()
        mock_pe_cls.return_value = mock_pe

        mock_check.return_value = [{"worker_id": "w1", "job_id": "j1"}]

        result = run_replay(force=False)

        assert result["status"] == "aborted"
        assert result["reason"] == "active_workers"
        mock_es.replay_events.assert_not_called()

    @patch("app.social_platform.tools.replay_social_system.check_active_workers")
    @patch("app.social_platform.tools.replay_social_system.SessionLocal")
    @patch("app.social_platform.tools.replay_social_system.EventStore")
    @patch("app.social_platform.tools.replay_social_system.ProjectionEngine")
    def test_proceeds_with_force_flag(self, mock_pe_cls, mock_es_cls, mock_session_cls, mock_check):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        mock_session.execute.return_value = result_mock

        mock_es = MagicMock()
        mock_es.replay_events.return_value = []
        mock_es_cls.return_value = mock_es
        mock_pe = MagicMock()
        mock_pe_cls.return_value = mock_pe

        mock_check.return_value = [{"worker_id": "w1", "job_id": "j1"}]

        result = run_replay(force=True)

        assert result["events_processed"] == 0
        assert "status" not in result

    @patch("app.social_platform.tools.replay_social_system.check_active_workers")
    @patch("app.social_platform.tools.replay_social_system.SessionLocal")
    @patch("app.social_platform.tools.replay_social_system.EventStore")
    @patch("app.social_platform.tools.replay_social_system.ProjectionEngine")
    def test_proceeds_when_no_workers_active(self, mock_pe_cls, mock_es_cls, mock_session_cls, mock_check):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        mock_session.execute.return_value = result_mock

        mock_es = MagicMock()
        mock_es.replay_events.return_value = []
        mock_es_cls.return_value = mock_es
        mock_pe = MagicMock()
        mock_pe_cls.return_value = mock_pe

        mock_check.return_value = []

        result = run_replay(force=False)

        assert result["events_processed"] == 0
