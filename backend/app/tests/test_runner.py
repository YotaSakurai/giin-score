"""パイプラインランナー (runner.py) テスト

CLI制御・パイプライン辞書・run_allフローのテスト。
"""

from unittest.mock import MagicMock, patch

from app.pipeline.runner import PIPELINES, SCHEDULED_PIPELINES, run_all


class TestPipelineRegistry:
    """PIPELINES辞書の整合性テスト。"""

    def test_all_scheduled_in_registry(self):
        """SCHEDULED_PIPELINESの全パイプラインがPIPELINESに登録されている。"""
        for name in SCHEDULED_PIPELINES:
            assert name in PIPELINES, (
                f"'{name}' is in SCHEDULED_PIPELINES "
                f"but not in PIPELINES"
            )

    def test_all_entries_callable(self):
        """PIPELINESの全エントリが呼び出し可能。"""
        for name, func in PIPELINES.items():
            assert callable(func), (
                f"PIPELINES['{name}'] is not callable"
            )

    def test_scoring_last_in_scheduled(self):
        """scoringはデータ収集後に実行されるため末尾付近にある。"""
        idx = SCHEDULED_PIPELINES.index("scoring")
        assert "speeches" in SCHEDULED_PIPELINES[:idx]
        assert "bills" in SCHEDULED_PIPELINES[:idx]

    def test_all_in_registry(self):
        """'all'がPIPELINESに登録されている。"""
        assert "all" in PIPELINES

    def test_minimum_pipelines(self):
        """最低限必要なパイプラインが存在する。"""
        required = [
            "members", "speeches", "bills",
            "votes", "scoring",
        ]
        for name in required:
            assert name in PIPELINES


class TestRunAll:
    @patch("app.pipeline.notify.notify_batch_complete")
    @patch("app.pipeline.notify.notify_pipeline_success")
    @patch("app.pipeline.notify.notify_batch_start")
    def test_all_success(
        self,
        mock_start,
        mock_success,
        mock_complete,
    ):
        """全パイプライン成功時のフロー。"""
        mock_db = MagicMock()
        mock_func = MagicMock(return_value=100)

        test_pipelines = {"test_a": mock_func, "test_b": mock_func}

        with (
            patch(
                "app.pipeline.runner.SCHEDULED_PIPELINES",
                ["test_a", "test_b"],
            ),
            patch(
                "app.pipeline.runner.PIPELINES",
                test_pipelines,
            ),
        ):
            run_all(mock_db, 215)

        mock_start.assert_called_once()
        assert mock_success.call_count == 2
        mock_complete.assert_called_once()
        results = mock_complete.call_args[0][1]
        assert len(results) == 2
        assert all(r["status"] == "ok" for r in results)

    @patch("app.pipeline.notify.notify_batch_complete")
    @patch("app.pipeline.notify.notify_pipeline_failure")
    @patch("app.pipeline.notify.notify_pipeline_success")
    @patch("app.pipeline.notify.notify_batch_start")
    def test_partial_failure(
        self,
        mock_start,
        mock_success,
        mock_failure,
        mock_complete,
    ):
        """一部パイプライン失敗時も他は継続実行される。"""
        mock_db = MagicMock()
        ok_func = MagicMock(return_value=50)
        fail_func = MagicMock(
            side_effect=RuntimeError("DB error")
        )

        test_pipelines = {
            "test_a": ok_func,
            "test_b": fail_func,
            "test_c": ok_func,
        }

        with (
            patch(
                "app.pipeline.runner.SCHEDULED_PIPELINES",
                ["test_a", "test_b", "test_c"],
            ),
            patch(
                "app.pipeline.runner.PIPELINES",
                test_pipelines,
            ),
        ):
            run_all(mock_db, 215)

        mock_failure.assert_called_once()
        assert mock_success.call_count == 2
        results = mock_complete.call_args[0][1]
        statuses = [r["status"] for r in results]
        assert statuses.count("ok") == 2
        assert statuses.count("error") == 1
