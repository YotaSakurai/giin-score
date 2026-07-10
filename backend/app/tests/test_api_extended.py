"""API / ミドルウェア / bias_detector の追加カバレッジテスト

カバレッジ 100% を目指して残りの分岐を網羅する。
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.member import Member
from app.models.review import UserReview
from app.models.score import MemberScore
from app.models.score_audit import ScoreAuditLog
from app.models.session import DietSession

# =====================================================================
# main.py: CacheControlMiddleware + health
# =====================================================================


class TestCacheControlMiddleware:
    def test_party_path_cache(self, client: TestClient):
        resp = client.get("/api/v1/scores/by-party")
        if resp.status_code == 200:
            assert "max-age=3600" in resp.headers.get("cache-control", "")

    def test_ranking_path_cache(self, client: TestClient):
        resp = client.get("/api/v1/scores/ranking")
        if resp.status_code == 200:
            assert "max-age=1800" in resp.headers.get("cache-control", "")

    def test_export_no_cache(self, client: TestClient):
        resp = client.get("/api/v1/scores/export/csv")
        assert "max-age" not in resp.headers.get("cache-control", "")

    def test_health_no_cache(self, client: TestClient):
        resp = client.get("/api/v1/health")
        cc = resp.headers.get("cache-control", "")
        assert "max-age" not in cc

    def test_members_cache(self, client: TestClient, db: Session):
        db.add(Member(id=1, name="テスト", chamber="representatives"))
        db.commit()

        resp = client.get("/api/v1/members/1")
        if resp.status_code == 200:
            assert "max-age=600" in resp.headers.get("cache-control", "")

    def test_default_cache(self, client: TestClient):
        resp = client.get("/api/v1/sessions")
        if resp.status_code == 200:
            cc = resp.headers.get("cache-control", "")
            assert "max-age=300" in cc or "max-age" not in cc


class TestHealthEndpoint:
    def test_health_ok(self, client: TestClient):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# =====================================================================
# bills.py: 分岐カバー
# =====================================================================


class TestBillsAPI:
    def test_list_with_session_not_found(self, client: TestClient):
        """存在しない会期番号でフィルタしても正常応答。"""
        resp = client.get("/api/v1/bills", params={"session_number": 999})
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_with_filters(self, client: TestClient, db: Session):
        """bill_kind, status, search フィルタの動作確認。"""
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(
            Bill(
                session_id=1,
                bill_kind="閣法",
                title="教育基本法改正案",
                status="成立",
            )
        )
        db.add(
            Bill(
                session_id=1,
                bill_kind="衆法",
                title="福祉推進法案",
                status="審議中",
            )
        )
        db.commit()

        resp = client.get("/api/v1/bills", params={"bill_kind": "閣法"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/bills", params={"status": "審議中"})
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/bills", params={"search": "教育"})
        assert resp.json()["total"] == 1

    def test_list_with_session_filter(self, client: TestClient, db: Session):
        """会期番号フィルタの動作確認。"""
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(Bill(session_id=1, bill_kind="閣法", title="テスト法案"))
        db.commit()

        resp = client.get("/api/v1/bills", params={"session_number": 215})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_bill_detail(self, client: TestClient, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        b = Bill(session_id=1, bill_kind="閣法", title="テスト法案")
        db.add(b)
        db.commit()

        resp = client.get(f"/api/v1/bills/{b.id}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "テスト法案"

    def test_get_bill_not_found(self, client: TestClient):
        resp = client.get("/api/v1/bills/99999")
        assert resp.status_code == 404


# =====================================================================
# reviews.py: 残り分岐
# =====================================================================


class TestReviewsAPI:
    def _create_review(self, db: Session, member_id: int = 1):
        if not db.query(DietSession).filter_by(id=1).first():
            db.add(DietSession(id=1, session_number=215, kind="通常"))
        if not db.query(Member).filter_by(id=1).first():
            db.add(Member(id=1, name="テスト議員", chamber="representatives"))
        db.flush()

        review = UserReview(
            member_id=member_id,
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

    def test_get_reviews_sort_newest(self, client: TestClient, db: Session):
        self._create_review(db)
        resp = client.get(
            "/api/v1/members/1/reviews",
            params={"sort": "newest"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_update_review_partial(self, client: TestClient, db: Session):
        review = self._create_review(db)
        resp = client.put(
            f"/api/v1/reviews/{review.id}",
            json={
                "reviewer_id": "user-123",
                "display_name": "更新名",
                "legislative_activity": 90,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "更新名"
        assert resp.json()["legislative_activity"] == 90

    def test_update_review_not_found(self, client: TestClient):
        resp = client.put(
            "/api/v1/reviews/99999",
            json={"reviewer_id": "user-123"},
        )
        assert resp.status_code == 404

    def test_update_review_forbidden(self, client: TestClient, db: Session):
        review = self._create_review(db)
        resp = client.put(
            f"/api/v1/reviews/{review.id}",
            json={"reviewer_id": "wrong-user"},
        )
        assert resp.status_code == 403

    def test_delete_review_not_found(self, client: TestClient):
        resp = client.delete(
            "/api/v1/reviews/99999",
            params={"reviewer_id": "user-123"},
        )
        assert resp.status_code == 404

    def test_delete_review_forbidden(self, client: TestClient, db: Session):
        review = self._create_review(db)
        resp = client.delete(
            f"/api/v1/reviews/{review.id}",
            params={"reviewer_id": "wrong-user"},
        )
        assert resp.status_code == 403

    def test_delete_review_success(self, client: TestClient, db: Session):
        review = self._create_review(db)
        resp = client.delete(
            f"/api/v1/reviews/{review.id}",
            params={"reviewer_id": "user-123"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_toggle_like(self, client: TestClient, db: Session):
        review = self._create_review(db)
        resp = client.post(
            f"/api/v1/reviews/{review.id}/like",
            json={"liker_id": "liker-1"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_liked"] is True
        assert resp.json()["like_count"] == 1

        resp = client.post(
            f"/api/v1/reviews/{review.id}/like",
            json={"liker_id": "liker-1"},
        )
        assert resp.json()["is_liked"] is False
        assert resp.json()["like_count"] == 0

    def test_toggle_like_not_found(self, client: TestClient):
        resp = client.post(
            "/api/v1/reviews/99999/like",
            json={"liker_id": "liker-1"},
        )
        assert resp.status_code == 404

    def test_review_summary(self, client: TestClient, db: Session):
        self._create_review(db)
        resp = client.get("/api/v1/members/1/review-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_count"] == 1
        assert data["average_total"] > 0


# =====================================================================
# bias_detector.py: run_bias_detection
# =====================================================================


class TestBiasDetection:
    def _seed_biased_data(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        for i in range(1, 6):
            db.add(Member(id=i, name=f"A議員{i}", chamber="representatives", party="政党A"))
        for i in range(6, 11):
            db.add(Member(id=i, name=f"B議員{i}", chamber="councillors", party="政党B"))
        db.flush()

        for i in range(1, 6):
            db.add(MemberScore(member_id=i, session_id=1, total=85, grade="A"))
        for i in range(6, 11):
            db.add(MemberScore(member_id=i, session_id=1, total=40, grade="D"))
        db.commit()

    @patch("app.pipeline.bias_detector._send_webhook")
    def test_detect_party_bias(self, mock_webhook, db: Session):
        from app.pipeline.bias_detector import detect_bias

        self._seed_biased_data(db)
        warnings = detect_bias(db, 215)
        assert any("政党間バイアス" in w for w in warnings)

    @patch("app.pipeline.bias_detector._send_webhook")
    def test_detect_chamber_bias(self, mock_webhook, db: Session):
        from app.pipeline.bias_detector import detect_bias

        self._seed_biased_data(db)
        warnings = detect_bias(db, 215)
        assert any("院別バイアス" in w for w in warnings)

    @patch("app.pipeline.bias_detector._send_webhook")
    def test_session_not_found(self, mock_webhook, db: Session):
        from app.pipeline.bias_detector import detect_bias

        warnings = detect_bias(db, 999)
        assert warnings == []

    @patch("app.pipeline.bias_detector._send_webhook")
    def test_grade_dominance(self, mock_webhook, db: Session):
        from app.pipeline.bias_detector import detect_bias

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        for i in range(1, 11):
            db.add(Member(id=i, name=f"議員{i}", chamber="representatives", party="党"))
        db.flush()

        for i in range(1, 9):
            db.add(MemberScore(member_id=i, session_id=1, total=85, grade="A"))
        for i in range(9, 11):
            db.add(MemberScore(member_id=i, session_id=1, total=30, grade="F"))
        db.commit()

        warnings = detect_bias(db, 215)
        assert any("グレード分布異常" in w for w in warnings)

    @patch("app.pipeline.bias_detector._send_webhook")
    def test_large_score_change(self, mock_webhook, db: Session):
        from app.pipeline.bias_detector import detect_bias

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(Member(id=1, name="変動議員", chamber="representatives", party="党"))
        db.flush()
        db.add(MemberScore(member_id=1, session_id=1, total=50, grade="C"))
        db.add(
            ScoreAuditLog(
                member_id=1,
                session_number=215,
                prev_total=30.0,
                new_total=80.0,
                diff_total=50.0,
                new_grade="A",
                new_legislative_activity=80.0,
                new_voting_behavior=70.0,
                new_policy_influence=60.0,
                new_transparency=50.0,
                new_question_quality=90.0,
            )
        )
        db.commit()

        warnings = detect_bias(db, 215)
        assert any("大幅スコア変動" in w for w in warnings)

    @patch("app.pipeline.bias_detector._send_webhook")
    def test_run_bias_detection_with_warnings(self, mock_webhook, db: Session):
        from app.pipeline.bias_detector import run_bias_detection

        self._seed_biased_data(db)
        count = run_bias_detection(db, 215)
        assert count > 0
        mock_webhook.assert_called_once()
        embed = mock_webhook.call_args[0][0]
        assert "バイアス検出レポート" in embed["title"]

    @patch("app.pipeline.bias_detector._send_webhook")
    def test_run_bias_detection_no_warnings(self, mock_webhook, db: Session):
        from app.pipeline.bias_detector import run_bias_detection

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        # スコア差が小さく、グレード分布も均等なデータ
        grades = ["A", "B", "C", "D", "F"]
        for i in range(1, 6):
            db.add(
                Member(
                    id=i,
                    name=f"議員{i}",
                    chamber="representatives",
                    party="党A",
                )
            )
        db.flush()
        for i in range(1, 6):
            db.add(
                MemberScore(
                    member_id=i,
                    session_id=1,
                    total=48 + i,
                    grade=grades[i - 1],
                )
            )
        db.commit()

        count = run_bias_detection(db, 215)
        assert count == 0
        mock_webhook.assert_called_once()
        embed = mock_webhook.call_args[0][0]
        assert "問題なし" in embed["title"]


# =====================================================================
# database.py: get_db
# =====================================================================


class TestGetDb:
    def test_get_db_generator(self):
        from app.database import get_db

        gen = get_db()
        db_session = next(gen)
        assert db_session is not None
        try:
            gen.send(None)
        except StopIteration:
            pass
