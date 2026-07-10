"""サービス・通知・セッション系テスト

ranking.py, notify.py, sessions API のテスト。
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.score import MemberScore
from app.models.session import DietSession
from app.pipeline.notify import (
    _send_webhook,
    notify_batch_complete,
    notify_batch_start,
    notify_pipeline_failure,
    notify_pipeline_success,
)
from app.services.ranking import get_ranking

# =====================================================================
# Sessions API
# =====================================================================


class TestSessionsAPI:
    def test_list_sessions(self, client: TestClient, db: Session):
        db.add_all(
            [
                DietSession(id=1, session_number=215, kind="通常"),
                DietSession(id=2, session_number=216, kind="臨時"),
            ]
        )
        db.commit()

        resp = client.get("/api/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # 降順
        assert data[0]["session_number"] == 216
        assert data[1]["session_number"] == 215

    def test_list_sessions_empty(self, client: TestClient, db: Session):
        resp = client.get("/api/v1/sessions")
        assert resp.status_code == 200
        assert resp.json() == []


# =====================================================================
# Ranking Service
# =====================================================================


@pytest.fixture()
def ranking_seed(db: Session):
    s = DietSession(id=1, session_number=215, kind="通常")
    db.add(s)
    db.flush()

    members = [
        Member(
            id=1,
            name="田中太郎",
            chamber="representatives",
            party="自由民主党",
            role_category="ruling_junior",
        ),
        Member(
            id=2,
            name="鈴木花子",
            chamber="councillors",
            party="立憲民主党",
            role_category="opposition_senior",
        ),
        Member(
            id=3,
            name="山田一郎",
            chamber="representatives",
            party="自由民主党",
            role_category="ruling_junior",
        ),
    ]
    db.add_all(members)
    db.flush()

    scores = [
        MemberScore(
            member_id=1,
            session_id=1,
            legislative_activity=80,
            voting_behavior=70,
            policy_influence=60,
            transparency=50,
            question_quality=90,
            total=72,
            grade="B",
        ),
        MemberScore(
            member_id=2,
            session_id=1,
            legislative_activity=90,
            voting_behavior=85,
            policy_influence=80,
            transparency=75,
            question_quality=95,
            total=86,
            grade="A",
        ),
        MemberScore(
            member_id=3,
            session_id=1,
            legislative_activity=30,
            voting_behavior=25,
            policy_influence=20,
            transparency=15,
            question_quality=10,
            total=22,
            grade="D",
        ),
    ]
    db.add_all(scores)
    db.commit()


class TestRankingService:
    def test_default_ranking(self, db: Session, ranking_seed):
        results = get_ranking(db)
        assert len(results) == 3
        # total降順
        assert results[0]["rank"] == 1
        assert results[0]["score"].total == 86
        assert results[1]["score"].total == 72
        assert results[2]["score"].total == 22

    def test_ranking_by_session(self, db: Session, ranking_seed):
        results = get_ranking(db, session_number=215)
        assert len(results) == 3

    def test_ranking_filter_chamber(self, db: Session, ranking_seed):
        results = get_ranking(db, chamber="representatives")
        assert len(results) == 2
        names = [r["member"].name for r in results]
        assert "鈴木花子" not in names

    def test_ranking_filter_party(self, db: Session, ranking_seed):
        results = get_ranking(db, party="自由民主党")
        assert len(results) == 2
        for r in results:
            assert r["member"].party == "自由民主党"

    def test_ranking_sort_by_axis(self, db: Session, ranking_seed):
        results = get_ranking(db, sort_by="legislative_activity")
        assert results[0]["score"].legislative_activity >= results[1]["score"].legislative_activity

    def test_ranking_limit_offset(self, db: Session, ranking_seed):
        results = get_ranking(db, limit=1, offset=0)
        assert len(results) == 1
        assert results[0]["rank"] == 1

        results2 = get_ranking(db, limit=1, offset=1)
        assert len(results2) == 1
        assert results2[0]["rank"] == 2

    def test_ranking_nonexistent_session(self, db: Session, ranking_seed):
        results = get_ranking(db, session_number=999)
        # session_number=999が見つからないと、
        # session_numberでフィルタしないまま返す
        assert isinstance(results, list)

    def test_ranking_filter_role_category(self, db: Session, ranking_seed):
        results = get_ranking(db, role_category="opposition_senior")
        assert len(results) == 1
        assert results[0]["member"].name == "鈴木花子"


# =====================================================================
# Notify
# =====================================================================


class TestSendWebhook:
    @patch("app.pipeline.notify.settings")
    def test_no_url_skips(self, mock_settings):
        mock_settings.discord_webhook_url = ""
        # 例外が出ないことを確認
        _send_webhook({"title": "test"})

    @patch("app.pipeline.notify.httpx.Client")
    @patch("app.pipeline.notify.settings")
    def test_sends_embed(self, mock_settings, mock_client_cls):
        mock_settings.discord_webhook_url = "https://hook.example"
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = lambda s: mock_client
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_resp

        _send_webhook({"title": "test", "color": 123})
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["embeds"][0]["title"] == "test"

    @patch("app.pipeline.notify.httpx.Client")
    @patch("app.pipeline.notify.settings")
    def test_exception_logged_not_raised(self, mock_settings, mock_client_cls):
        mock_settings.discord_webhook_url = "https://hook.example"
        mock_client_cls.return_value.__enter__ = MagicMock(side_effect=Exception("network error"))
        # 例外が出ないことを確認
        _send_webhook({"title": "test"})


class TestNotifyFunctions:
    @patch("app.pipeline.notify._send_webhook")
    def test_batch_start(self, mock_webhook):
        notify_batch_start(215, ["speeches", "bills"])
        mock_webhook.assert_called_once()
        embed = mock_webhook.call_args[0][0]
        assert "215" in embed["description"]
        assert "speeches" in embed["description"]

    @patch("app.pipeline.notify._send_webhook")
    def test_pipeline_success(self, mock_webhook):
        notify_pipeline_success("speeches", 1000, 30.5)
        embed = mock_webhook.call_args[0][0]
        assert "1000" in embed["description"]
        assert "30.5" in embed["description"]
        assert "✅" in embed["title"]

    @patch("app.pipeline.notify._send_webhook")
    def test_pipeline_failure(self, mock_webhook):
        notify_pipeline_failure("scoring", "DB error", 5.0)
        embed = mock_webhook.call_args[0][0]
        assert "DB error" in embed["description"]
        assert "❌" in embed["title"]

    @patch("app.pipeline.notify._send_webhook")
    def test_pipeline_failure_truncates(self, mock_webhook):
        long_error = "x" * 1000
        notify_pipeline_failure("scoring", long_error, 5.0)
        embed = mock_webhook.call_args[0][0]
        assert len(embed["description"]) < 600

    @patch("app.pipeline.notify._send_webhook")
    def test_batch_complete_all_success(self, mock_webhook):
        results = [
            {
                "name": "speeches",
                "status": "ok",
                "records": 100,
                "elapsed": 10.0,
            },
            {
                "name": "bills",
                "status": "ok",
                "records": 50,
                "elapsed": 5.0,
            },
        ]
        notify_batch_complete(215, results, 15.0)
        embed = mock_webhook.call_args[0][0]
        assert "🎉" in embed["title"]
        assert "2成功" in embed["description"]
        assert "0失敗" in embed["description"]

    @patch("app.pipeline.notify._send_webhook")
    def test_batch_complete_with_failures(self, mock_webhook):
        results = [
            {
                "name": "speeches",
                "status": "ok",
                "records": 100,
                "elapsed": 10.0,
            },
            {
                "name": "scoring",
                "status": "error",
                "records": 0,
                "error": "DB down",
                "elapsed": 1.0,
            },
        ]
        notify_batch_complete(215, results, 11.0)
        embed = mock_webhook.call_args[0][0]
        assert "⚠️" in embed["title"]
        assert "1成功" in embed["description"]
        assert "1失敗" in embed["description"]
