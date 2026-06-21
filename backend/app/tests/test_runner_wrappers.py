"""runner.py の run_* ラッパー関数と main() のテスト

各 run_* は内部関数をインポートして呼ぶだけなので、
内部関数をモックして呼び出し契約を検証する。
"""

from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.runner import (
    run_analyze,
    run_bills,
    run_members,
    run_profiles,
    run_scoring,
    run_shugiin,
    run_smartnews,
    run_speech_quality,
    run_speeches,
    run_votes,
    run_written_questions,
)


class TestRunMembers:
    @patch("app.pipeline.runner.run_members.__module__", new="app.pipeline.runner")
    @patch("app.pipeline.kokkai_api.fetch_speeches", return_value=42)
    def test_delegates(self, mock_fetch):
        db = MagicMock()
        result = run_members(db, 215)
        mock_fetch.assert_called_once_with(db, 215)
        assert result == 42


class TestRunSpeeches:
    @patch("app.pipeline.kokkai_api.fetch_speeches", return_value=100)
    @patch("app.pipeline.kokkai_api.get_last_run", return_value=0)
    def test_no_resume(self, mock_last, mock_fetch):
        db = MagicMock()
        result = run_speeches(db, 215)
        mock_last.assert_called_once_with(db, 215)
        mock_fetch.assert_called_once_with(db, 215, resume_from=0)
        assert result == 100

    @patch("app.pipeline.kokkai_api.fetch_speeches", return_value=50)
    @patch("app.pipeline.kokkai_api.get_last_run", return_value=500)
    def test_resume(self, mock_last, mock_fetch):
        db = MagicMock()
        result = run_speeches(db, 215)
        mock_fetch.assert_called_once_with(db, 215, resume_from=500)
        assert result == 50


class TestRunBills:
    @patch("app.pipeline.shugiin_scraper.scrape_bills_list", return_value=30)
    def test_delegates(self, mock_scrape):
        db = MagicMock()
        assert run_bills(db, 215) == 30
        mock_scrape.assert_called_once_with(db, 215)


class TestRunVotes:
    @patch("app.pipeline.sangiin_scraper.scrape_votes", return_value=20)
    def test_delegates(self, mock_scrape):
        db = MagicMock()
        assert run_votes(db, 215) == 20
        mock_scrape.assert_called_once_with(db, 215)


class TestRunShugiin:
    @patch("app.pipeline.shugiin_scraper.scrape_bills", return_value=15)
    def test_delegates(self, mock_scrape):
        db = MagicMock()
        assert run_shugiin(db, 215) == 15
        mock_scrape.assert_called_once_with(db, 215)


class TestRunScoring:
    @patch("app.services.scoring.compute_scores_for_session", return_value=200)
    def test_delegates(self, mock_compute):
        db = MagicMock()
        assert run_scoring(db, 215) == 200
        mock_compute.assert_called_once_with(db, 215)


class TestRunSmartNews:
    @patch("app.pipeline.smartnews_loader.load_bills_csv", return_value=10)
    def test_delegates(self, mock_load):
        db = MagicMock()
        assert run_smartnews(db, 215) == 10
        mock_load.assert_called_once_with(db)


class TestRunProfiles:
    @patch("app.pipeline.member_profile_scraper.scrape_member_profiles", return_value=50)
    def test_delegates(self, mock_scrape):
        db = MagicMock()
        assert run_profiles(db, 215) == 50
        mock_scrape.assert_called_once_with(db)


class TestRunWrittenQuestions:
    @patch("app.pipeline.shitsumon_scraper.scrape_written_questions", return_value=25)
    def test_delegates(self, mock_scrape):
        db = MagicMock()
        assert run_written_questions(db, 215) == 25
        mock_scrape.assert_called_once_with(db, 215)


class TestRunSpeechQuality:
    @patch("app.pipeline.speech_quality.analyze_speeches_for_session", return_value=80)
    def test_delegates(self, mock_analyze):
        db = MagicMock()
        assert run_speech_quality(db, 215) == 80
        mock_analyze.assert_called_once_with(db, 215)


class TestRunAnalyze:
    @patch("app.pipeline.analyze.analyze_data_quality", return_value=1)
    def test_delegates(self, mock_analyze):
        db = MagicMock()
        assert run_analyze(db, 215) == 1
        mock_analyze.assert_called_once_with(db, 215)


class TestMain:
    @patch("app.pipeline.runner.SessionLocal")
    @patch("sys.argv", ["runner", "--pipeline", "scoring", "--session", "215"])
    def test_main_success(self, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        with patch("app.services.scoring.compute_scores_for_session", return_value=5):
            from app.pipeline.runner import main
            main()

        mock_db.close.assert_called_once()

    @patch("app.pipeline.runner.SessionLocal")
    @patch("sys.argv", ["runner", "--pipeline", "scoring", "--session", "215"])
    def test_main_failure(self, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        with (
            patch(
                "app.services.scoring.compute_scores_for_session",
                side_effect=RuntimeError("boom"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            from app.pipeline.runner import main
            main()

        assert exc_info.value.code == 1
        mock_db.close.assert_called_once()
