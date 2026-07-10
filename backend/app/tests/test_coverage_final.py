"""最終カバレッジ向上テスト

members.py, scores.py, reviews.py, smartnews_loader.py, kokkai_api.py,
scoring.py, main.py の残りの未カバー分岐を網羅する。
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.member import Member
from app.models.review import UserReview
from app.models.score import MemberScore
from app.models.session import DietSession
from app.models.vote import VoteRecord, VoteResult

# =====================================================================
# members.py: フィルタ分岐 (lines 102-103, 223, 413-450, 746, 779-806)
# =====================================================================


class TestMembersFilters:
    def _seed(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(
            Member(
                id=1,
                name="田中太郎",
                chamber="representatives",
                party="自由民主党",
                district="東京1区",
                role_category="member",
            )
        )
        db.add(
            Member(
                id=2,
                name="鈴木花子",
                chamber="councillors",
                party="立憲民主党",
                district="神奈川",
                role_category="member",
            )
        )
        db.flush()
        db.add(
            MemberScore(
                member_id=1,
                session_id=1,
                total=70,
                grade="B",
                legislative_activity=60,
                voting_behavior=70,
                policy_influence=50,
                transparency=40,
                question_quality=80,
            )
        )
        db.add(
            MemberScore(
                member_id=2,
                session_id=1,
                total=55,
                grade="C",
                legislative_activity=50,
                voting_behavior=55,
                policy_influence=45,
                transparency=35,
                question_quality=65,
            )
        )
        db.commit()

    def test_role_category_filter(self, client: TestClient, db: Session):
        """role_category フィルタ (lines 102-103)。"""
        self._seed(db)
        resp = client.get("/api/v1/members", params={"role_category": "member"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_district_filter(self, client: TestClient, db: Session):
        """district フィルタ (lines 104-106)。"""
        self._seed(db)
        resp = client.get("/api/v1/members", params={"district": "東京"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_sort_order_asc(self, client: TestClient, db: Session):
        """sort_order=asc (line 223)。"""
        self._seed(db)
        resp = client.get("/api/v1/members", params={"sort_order": "asc"})
        assert resp.status_code == 200

    def test_member_scores_history(self, client: TestClient, db: Session):
        """議員スコア履歴 (lines 413-450)。"""
        self._seed(db)
        resp = client.get("/api/v1/members/1/scores")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["session_number"] == 215

    def test_member_scores_not_found(self, client: TestClient, db: Session):
        resp = client.get("/api/v1/members/99999/scores")
        assert resp.status_code == 404

    def test_vote_pattern_empty(self, client: TestClient, db: Session):
        """投票パターン - 投票記録なし (line 746)。"""
        self._seed(db)
        resp = client.get("/api/v1/members/1/vote-pattern")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_votes"] == 0

    def test_vote_pattern_with_data(self, client: TestClient, db: Session):
        """投票パターン - 投票データあり (lines 779-806)。"""
        self._seed(db)
        bill = Bill(session_id=1, bill_kind="閣法", title="テスト法案")
        db.add(bill)
        db.flush()
        vr = VoteResult(bill_id=bill.id, chamber="representatives", ayes=10, nays=5, result="可決")
        db.add(vr)
        db.flush()
        # 同党の他議員の投票（多数派判定用）
        db.add(Member(id=3, name="佐藤三郎", chamber="representatives", party="自由民主党"))
        db.flush()
        db.add(VoteRecord(vote_result_id=vr.id, member_id=1, vote="aye"))
        db.add(VoteRecord(vote_result_id=vr.id, member_id=3, vote="aye"))
        # absent
        vr2 = VoteResult(bill_id=bill.id, chamber="representatives", ayes=5, nays=10, result="否決")
        db.add(vr2)
        db.flush()
        db.add(VoteRecord(vote_result_id=vr2.id, member_id=1, vote="absent"))
        db.commit()

        resp = client.get("/api/v1/members/1/vote-pattern")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_votes"] >= 1
        assert data["absent_count"] >= 1


# =====================================================================
# scores.py: _resolve_session_id, ranking filters (lines 37-40, 93-100, 338, 353)
# =====================================================================


class TestScoresAPI:
    def _seed(self, db: Session):
        s1 = DietSession(id=1, session_number=214, kind="通常")
        s2 = DietSession(id=2, session_number=215, kind="通常")
        db.add_all([s1, s2])
        db.flush()

        m1 = Member(
            id=1,
            name="議員A",
            chamber="representatives",
            party="党A",
            role_category="member",
        )
        m2 = Member(id=2, name="議員B", chamber="councillors", party="党B", role_category="member")
        db.add_all([m1, m2])
        db.flush()

        db.add(
            MemberScore(
                member_id=1,
                session_id=1,
                total=50,
                grade="C",
                legislative_activity=50,
                voting_behavior=50,
                policy_influence=50,
                transparency=50,
                question_quality=50,
            )
        )
        db.add(
            MemberScore(
                member_id=1,
                session_id=2,
                total=70,
                grade="B",
                legislative_activity=60,
                voting_behavior=70,
                policy_influence=65,
                transparency=55,
                question_quality=80,
            )
        )
        db.add(
            MemberScore(
                member_id=2,
                session_id=2,
                total=60,
                grade="C",
                legislative_activity=55,
                voting_behavior=60,
                policy_influence=55,
                transparency=50,
                question_quality=70,
            )
        )
        db.commit()

    def test_resolve_session_by_number(self, client: TestClient, db: Session):
        """session_number指定 (lines 37-40)。"""
        self._seed(db)
        resp = client.get("/api/v1/scores/ranking", params={"session_number": 215})
        assert resp.status_code == 200

    def test_ranking_with_chamber(self, client: TestClient, db: Session):
        """chamber フィルタ (line 93)。"""
        self._seed(db)
        resp = client.get("/api/v1/scores/ranking", params={"chamber": "representatives"})
        assert resp.status_code == 200

    def test_ranking_with_party(self, client: TestClient, db: Session):
        """party フィルタ (line 98)。"""
        self._seed(db)
        resp = client.get("/api/v1/scores/ranking", params={"party": "党A"})
        assert resp.status_code == 200

    def test_ranking_with_role_category(self, client: TestClient, db: Session):
        """role_category フィルタ (line 100)。"""
        self._seed(db)
        resp = client.get("/api/v1/scores/ranking", params={"role_category": "member"})
        assert resp.status_code == 200

    def test_movers_no_data(self, client: TestClient, db: Session):
        """movers - セッション1つだけ (line 338)。"""
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(Member(id=1, name="議員A", chamber="representatives"))
        db.flush()
        db.add(
            MemberScore(
                member_id=1,
                session_id=1,
                total=50,
                grade="C",
                legislative_activity=50,
                voting_behavior=50,
                policy_influence=50,
                transparency=50,
                question_quality=50,
            )
        )
        db.commit()

        resp = client.get("/api/v1/scores/movers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["risers"] == []
        assert data["fallers"] == []

    def test_movers_with_chamber(self, client: TestClient, db: Session):
        """movers + chamber (line 353)。"""
        self._seed(db)
        resp = client.get("/api/v1/scores/movers", params={"chamber": "representatives"})
        assert resp.status_code == 200


# =====================================================================
# reviews.py: partial update lines (205, 207, 209, 211)
# =====================================================================


class TestReviewsPartialUpdate:
    def _create_review(self, db: Session):
        if not db.query(Member).filter_by(id=1).first():
            db.add(Member(id=1, name="テスト議員", chamber="representatives"))
            db.flush()

        review = UserReview(
            member_id=1,
            reviewer_id="user-123",
            display_name="テストユーザー",
            legislative_activity=80,
            voting_behavior=70,
            policy_influence=60,
            transparency=50,
            question_quality=40,
            total=60,
            comment="テスト",
        )
        db.add(review)
        db.commit()
        return review

    def test_update_all_score_fields(self, client: TestClient, db: Session):
        """全スコアフィールドの部分更新 (lines 205-211)。"""
        review = self._create_review(db)
        resp = client.put(
            f"/api/v1/reviews/{review.id}",
            json={
                "reviewer_id": "user-123",
                "voting_behavior": 90,
                "policy_influence": 85,
                "transparency": 80,
                "question_quality": 75,
                "comment": "更新コメント",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["voting_behavior"] == 90
        assert data["policy_influence"] == 85
        assert data["transparency"] == 80
        assert data["question_quality"] == 75
        assert data["comment"] == "更新コメント"
        # totalが再計算されている
        assert data["total"] > 0


# =====================================================================
# reviews.py: _to_response fallback DB query (line 33)
# =====================================================================


class TestToResponseFallback:
    def test_liker_check_without_selectinload(self, client: TestClient, db: Session):
        """selectinloadなしでのliker_id確認 (line 33)。"""
        from app.api.reviews import _to_response

        db.add(Member(id=1, name="テスト議員", chamber="representatives"))
        db.flush()

        review = UserReview(
            member_id=1,
            reviewer_id="user-123",
            display_name="テスト",
            legislative_activity=50,
            voting_behavior=50,
            policy_influence=50,
            transparency=50,
            question_quality=50,
            total=50,
            comment="test",
        )
        db.add(review)
        db.commit()

        # selectinloadなし → フォールバックDBクエリを使用
        # likesがロードされていないfresh objectで呼ぶ
        review_raw = db.query(UserReview).filter_by(id=review.id).first()
        # hasattr + likes is not None チェックをバイパスし、DB fallbackを使う
        result = _to_response(review_raw, "user-999", db)
        assert result["is_liked"] is False


# =====================================================================
# smartnews_loader.py: exception in pipeline (lines 68-73)
# =====================================================================


class TestSmartNewsLoaderException:
    def test_pipeline_exception(self, db: Session):
        """処理中の例外でfailedマーク (lines 68-73)。"""
        import tempfile

        from app.pipeline.smartnews_loader import load_bills_csv

        # pandas.read_csvをモックして例外を発生させる（行処理ではなくファイル読み込みレベル）
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("session,title\n215,テスト\n")
            csv_path = f.name

        with patch(
            "app.pipeline.smartnews_loader.pd.read_csv",
            side_effect=RuntimeError("forced error"),
        ):
            try:
                load_bills_csv(db, csv_path=csv_path)
            except RuntimeError:
                pass

        from app.models.pipeline import PipelineRun

        run = db.query(PipelineRun).filter_by(pipeline_name="smartnews_bills").first()
        assert run.status == "failed"


# =====================================================================
# kokkai_api.py: batch commit, process error (lines 72, 78-83)
# =====================================================================


class TestFetchSpeechesEdgeCases:
    @patch("app.pipeline.kokkai_api.time.sleep")
    def test_process_record_error_continues(self, mock_sleep, db: Session):
        """発言レコード処理エラーでもスキップして続行 (lines 78-79)。"""
        import httpx

        from app.pipeline.kokkai_api import fetch_speeches

        records = [
            {
                "speaker": "田中太郎",
                "nameOfHouse": "衆議院",
                "speech": "テスト" * 50,
                "date": "2024-01-01",
                "speechURL": f"https://example.com/speech/{i}",
            }
            for i in range(3)
        ]

        responses = [
            httpx.Response(
                200,
                json={"numberOfRecords": 3, "speechRecord": records},
                request=httpx.Request("GET", "https://example.com"),
            ),
            httpx.Response(
                200,
                json={"numberOfRecords": 0, "speechRecord": []},
                request=httpx.Request("GET", "https://example.com"),
            ),
        ]

        mock_client = MagicMock()
        mock_client.get.side_effect = responses
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.kokkai_api.httpx.Client", return_value=mock_client):
            result = fetch_speeches(db, 215)

        assert result >= 1

    @patch("app.pipeline.kokkai_api.time.sleep")
    def test_empty_speech_records(self, mock_sleep, db: Session):
        """speechRecordが空リスト (line 72)。"""
        import httpx

        from app.pipeline.kokkai_api import fetch_speeches

        resp = httpx.Response(
            200,
            json={"numberOfRecords": 10, "speechRecord": []},
            request=httpx.Request("GET", "https://example.com"),
        )

        mock_client = MagicMock()
        mock_client.get.return_value = resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.kokkai_api.httpx.Client", return_value=mock_client):
            result = fetch_speeches(db, 215)

        assert result == 0


# =====================================================================
# main.py: health degraded (lines 143-144)
# =====================================================================


class TestHealthDegraded:
    def test_health_db_failure(self, db: Session):
        """DB接続失敗でdegraded応答。"""
        from app.database import get_db
        from app.main import app

        def broken_db():
            mock = MagicMock()
            mock.execute.side_effect = Exception("connection refused")
            yield mock

        app.dependency_overrides[get_db] = broken_db
        try:
            with TestClient(app) as c:
                resp = c.get("/api/v1/health")
                assert resp.status_code == 200
                assert resp.json()["status"] == "degraded"
                assert resp.json()["database"] == "disconnected"
        finally:
            app.dependency_overrides.clear()


# =====================================================================
# bias_detector.py: grade total=0 (line 114)
# =====================================================================


class TestBiasEdge:
    @patch("app.pipeline.bias_detector._send_webhook")
    def test_empty_grade_distribution(self, mock_webhook, db: Session):
        """スコアが0件の場合 (line 114)。"""
        from app.pipeline.bias_detector import _check_grade_distribution

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        warnings = _check_grade_distribution(db, s)
        assert warnings == []
