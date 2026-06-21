"""kokkai_api.py fetch_speeches のテスト（HTTPモック版）"""

from unittest.mock import MagicMock, patch

import httpx
from sqlalchemy.orm import Session

from app.models.pipeline import PipelineRun
from app.models.session import DietSession
from app.pipeline.kokkai_api import fetch_speeches


def _make_response(records: list[dict], total: int) -> httpx.Response:
    """モック用のhttpx.Responseを生成する。"""
    body = {
        "numberOfRecords": total,
        "speechRecord": records,
    }
    return httpx.Response(
        200,
        json=body,
        request=httpx.Request("GET", "https://example.com"),
    )


def _empty_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={"numberOfRecords": 0, "speechRecord": []},
        request=httpx.Request("GET", "https://example.com"),
    )


class TestFetchSpeeches:
    @patch("app.pipeline.kokkai_api.time.sleep")
    def test_basic_single_page(self, mock_sleep, db: Session):
        """1ページ分の発言を取得してDBに保存する。"""
        records = [
            {
                "speaker": "田中太郎",
                "speakerGroup": "自民党",
                "speakerPosition": "",
                "nameOfHouse": "衆議院",
                "nameOfMeeting": "予算委員会",
                "speech": "テスト発言" * 20,
                "date": "2024-03-01",
                "speechURL": f"https://example.com/speech/{i}",
            }
            for i in range(3)
        ]
        responses = [
            _make_response(records, 3),
            _empty_response(),
        ]

        mock_client = MagicMock()
        mock_client.get.side_effect = responses
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.kokkai_api.httpx.Client", return_value=mock_client):
            result = fetch_speeches(db, 215)

        assert result == 3
        # pipeline_run が completed になっている
        run = db.query(PipelineRun).filter_by(pipeline_name="kokkai_speeches").first()
        assert run.status == "completed"

    @patch("app.pipeline.kokkai_api.time.sleep")
    def test_creates_diet_session(self, mock_sleep, db: Session):
        """DietSessionが存在しない場合に自動作成する。"""
        mock_client = MagicMock()
        mock_client.get.return_value = _empty_response()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.kokkai_api.httpx.Client", return_value=mock_client):
            fetch_speeches(db, 999)

        session = db.query(DietSession).filter_by(session_number=999).first()
        assert session is not None

    @patch("app.pipeline.kokkai_api.time.sleep")
    def test_resume_from(self, mock_sleep, db: Session):
        """resume_from指定時にstartRecordがオフセットされる。"""
        mock_client = MagicMock()
        mock_client.get.return_value = _empty_response()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.kokkai_api.httpx.Client", return_value=mock_client):
            fetch_speeches(db, 215, resume_from=500)

        call_args = mock_client.get.call_args
        params = call_args[1].get("params", call_args[0][1] if len(call_args[0]) > 1 else {})
        # startRecord は 501 から始まるべき
        if isinstance(params, dict):
            assert params.get("startRecord") == 501

    @patch("app.pipeline.kokkai_api.time.sleep")
    def test_http_error_breaks_loop(self, mock_sleep, db: Session):
        """HTTPエラー時にループを中断する。"""
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=httpx.Request("GET", "https://example.com"),
            response=httpx.Response(500),
        )
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.kokkai_api.httpx.Client", return_value=mock_client):
            result = fetch_speeches(db, 215)

        assert result == 0
        run = db.query(PipelineRun).filter_by(pipeline_name="kokkai_speeches").first()
        assert run.status == "completed"

    @patch("app.pipeline.kokkai_api.time.sleep")
    def test_exception_marks_failed(self, mock_sleep, db: Session):
        """想定外のException時にpipeline_runがfailedになる。"""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(side_effect=RuntimeError("connection refused"))
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.kokkai_api.httpx.Client", return_value=mock_client):
            try:
                fetch_speeches(db, 215)
            except RuntimeError:
                pass

        run = db.query(PipelineRun).filter_by(pipeline_name="kokkai_speeches").first()
        assert run.status == "failed"
        assert run.error_message is not None
