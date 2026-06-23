"""居眠り検出のテスト"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.member import Member
from app.models.session import DietSession
from app.models.sleeping_detection import SleepingDetection

try:
    import cv2  # noqa: F401
    import numpy as np

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

requires_cv2 = pytest.mark.skipif(not HAS_CV2, reason="opencv/numpy not installed")


@pytest.fixture()
def sleeping_data(db):
    """居眠り検出テスト用のシードデータ"""
    session = DietSession(id=1, session_number=215, kind="通常")
    db.add(session)

    members = [
        Member(id=1, name="田中太郎", chamber="representatives", party="自由民主党"),
        Member(id=2, name="鈴木花子", chamber="councillors", party="立憲民主党"),
    ]
    db.add_all(members)

    detections = [
        SleepingDetection(
            id=1,
            member_id=1,
            session_id=1,
            video_url="https://example.com/video1.mp4",
            video_date=datetime(2026, 6, 1),
            meeting_name="予算委員会",
            start_time_sec=300.0,
            end_time_sec=420.0,
            duration_sec=120.0,
            detection_type="head_forward",
            confidence=0.85,
            head_angle_avg=42.5,
            screenshot_path="/data/sleeping_evidence/sleep_1_300_0.jpg",
            review_status="pending",
            detected_at=datetime(2026, 6, 1, 10, 0),
        ),
        SleepingDetection(
            id=2,
            member_id=1,
            session_id=1,
            video_url="https://example.com/video2.mp4",
            meeting_name="本会議",
            start_time_sec=600.0,
            end_time_sec=780.0,
            duration_sec=180.0,
            detection_type="head_backward",
            confidence=0.92,
            head_angle_avg=35.0,
            review_status="approved",
            reviewed_at=datetime(2026, 6, 2),
            detected_at=datetime(2026, 6, 1, 14, 0),
        ),
        SleepingDetection(
            id=3,
            member_id=2,
            session_id=1,
            video_url="https://example.com/video3.mp4",
            meeting_name="厚生労働委員会",
            start_time_sec=100.0,
            end_time_sec=200.0,
            duration_sec=100.0,
            detection_type="head_forward",
            confidence=0.65,
            review_status="rejected",
            review_note="資料を読んでいるだけ",
            detected_at=datetime(2026, 6, 1, 11, 0),
        ),
    ]
    db.add_all(detections)
    db.commit()
    return members, detections


class TestSleepingAPI:
    """居眠り検出APIのテスト"""

    def test_list_detections(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/detections")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_list_detections_filter_status(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/detections?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["review_status"] == "pending"

    def test_list_detections_filter_member(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/detections?member_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_get_detection(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/detections/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert data["detection_type"] == "head_forward"
        assert data["member_name"] == "田中太郎"
        assert data["confidence"] == 0.85

    def test_get_detection_not_found(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/detections/999")
        assert resp.status_code == 404

    def test_review_approve(self, client, sleeping_data):
        resp = client.put(
            "/api/v1/sleeping/detections/1/review",
            json={"status": "approved", "note": "明らかに居眠り"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "approved"
        assert data["review_note"] == "明らかに居眠り"
        assert data["reviewed_at"] is not None

    def test_review_reject(self, client, sleeping_data):
        resp = client.put(
            "/api/v1/sleeping/detections/1/review",
            json={"status": "rejected", "note": "資料を読んでいる"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["review_status"] == "rejected"

    def test_review_with_member_assignment(self, client, sleeping_data):
        """レビュー時に議員を手動紐付けできる"""
        resp = client.put(
            "/api/v1/sleeping/detections/1/review",
            json={"status": "approved", "member_id": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["member_id"] == 2
        assert data["identified_by"] == "manual"

    def test_review_invalid_status(self, client, sleeping_data):
        resp = client.put(
            "/api/v1/sleeping/detections/1/review",
            json={"status": "invalid"},
        )
        assert resp.status_code == 400

    def test_review_nonexistent_member(self, client, sleeping_data):
        resp = client.put(
            "/api/v1/sleeping/detections/1/review",
            json={"status": "approved", "member_id": 999},
        )
        assert resp.status_code == 400

    def test_stats(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_detections"] == 3
        assert data["pending"] == 1
        assert data["approved"] == 1
        assert data["rejected"] == 1
        assert data["members_with_incidents"] == 1

    def test_member_incidents(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/members/1/incidents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["member_name"] == "田中太郎"
        assert data["total_incidents"] == 1  # approved のみ
        assert data["incidents"][0]["detection_type"] == "head_backward"

    def test_member_incidents_not_found(self, client, sleeping_data):
        resp = client.get("/api/v1/sleeping/members/999/incidents")
        assert resp.status_code == 404


class TestSleepingPenalty:
    """居眠りペナルティのスコアリング統合テスト"""

    def test_penalty_computation(self, db, sleeping_data):
        from app.services.scoring import _compute_sleeping_penalties_bulk

        session = db.query(DietSession).first()
        penalties = _compute_sleeping_penalties_bulk(db, session)

        # member_id=1 は approved が 1件
        assert 1 in penalties
        assert penalties[1]["count"] == 1
        assert penalties[1]["penalty"] == 3.0  # 1件 × 3.0

        # member_id=2 は rejected なのでペナルティなし
        assert 2 not in penalties

    def test_penalty_cap(self, db):
        """ペナルティ上限のテスト"""
        session = DietSession(id=1, session_number=215, kind="通常")
        member = Member(id=1, name="テスト太郎", chamber="representatives")
        db.add_all([session, member])

        # 6件の承認済み居眠り (6 × 3.0 = 18.0 だが cap は 15.0)
        for i in range(6):
            db.add(
                SleepingDetection(
                    member_id=1,
                    session_id=1,
                    video_url=f"https://example.com/v{i}.mp4",
                    start_time_sec=float(i * 1000),
                    end_time_sec=float(i * 1000 + 120),
                    duration_sec=120.0,
                    detection_type="head_forward",
                    confidence=0.9,
                    review_status="approved",
                    detected_at=datetime(2026, 6, 1),
                )
            )
        db.commit()

        from app.services.scoring import _compute_sleeping_penalties_bulk

        penalties = _compute_sleeping_penalties_bulk(db, session)
        assert penalties[1]["count"] == 6
        assert penalties[1]["penalty"] == 15.0  # キャップ適用


@requires_cv2
class TestDetectorComponents:
    """検出コンポーネントの単体テスト (opencv/numpy必須)"""

    def test_face_tracker_no_sleeping_short_duration(self):
        """持続時間が短い場合は居眠りと判定しない"""
        from app.pipeline.sleeping_detector import _FaceTracker

        tracker = _FaceTracker(0, (100, 100), 0.0)
        for t in range(0, 30, 5):
            tracker.update(
                pitch=40.0,
                yaw=0.0,
                roll=0.0,
                center=(100, 100),
                time_sec=float(t),
                frame=np.zeros((100, 100, 3), dtype=np.uint8),
            )

        result = tracker.check_sleeping()
        assert result is None

    def test_face_tracker_sleeping_forward(self):
        """前傾居眠りの検出"""
        from app.pipeline.sleeping_detector import _FaceTracker

        tracker = _FaceTracker(0, (100, 100), 0.0)
        for t in range(0, 91, 5):
            tracker.update(
                pitch=45.0,
                yaw=0.0,
                roll=0.0,
                center=(100, 100),
                time_sec=float(t),
                frame=np.zeros((100, 100, 3), dtype=np.uint8),
            )

        result = tracker.check_sleeping()
        assert result is not None
        assert result["type"] == "head_forward"
        assert result["duration"] >= 60.0
        assert result["confidence"] > 0.0

    def test_face_tracker_sleeping_backward(self):
        """仰向け居眠りの検出"""
        from app.pipeline.sleeping_detector import _FaceTracker

        tracker = _FaceTracker(0, (100, 100), 0.0)
        for t in range(0, 91, 5):
            tracker.update(
                pitch=-35.0,
                yaw=0.0,
                roll=0.0,
                center=(100, 100),
                time_sec=float(t),
                frame=np.zeros((100, 100, 3), dtype=np.uint8),
            )

        result = tracker.check_sleeping()
        assert result is not None
        assert result["type"] == "head_backward"

    def test_face_tracker_high_motion_no_sleeping(self):
        """動きが多い場合は居眠りと判定しない"""
        from app.pipeline.sleeping_detector import _FaceTracker

        tracker = _FaceTracker(0, (100, 100), 0.0)
        for t in range(0, 91, 5):
            x = 100 + (t % 20) * 10
            tracker.update(
                pitch=40.0,
                yaw=0.0,
                roll=0.0,
                center=(x, 100),
                time_sec=float(t),
                frame=np.zeros((100, 100, 3), dtype=np.uint8),
            )

        result = tracker.check_sleeping()
        assert result is None

    def test_match_tracker(self):
        """トラッカーマッチングのテスト"""
        from app.pipeline.sleeping_detector import _FaceTracker, _match_tracker

        trackers = {
            0: _FaceTracker(0, (100, 100), 0.0),
            1: _FaceTracker(1, (500, 300), 0.0),
        }

        assert _match_tracker(trackers, (105, 102), 1920) == 0
        assert _match_tracker(trackers, (510, 305), 1920) == 1
        assert _match_tracker(trackers, (1000, 800), 1920) == 2

    def test_download_diet_video_no_ytdlp(self):
        """yt-dlpが見つからない場合"""
        from app.pipeline.sleeping_detector import download_diet_video

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = download_diet_video("https://example.com/video.mp4")
            assert result is None

    def test_get_video_urls_from_env(self):
        """環境変数から動画URL取得"""
        from app.pipeline.sleeping_detector import _get_video_urls

        with patch.dict(
            "os.environ",
            {"SLEEPING_VIDEO_URLS": "https://a.com/1.mp4,https://b.com/2.mp4"},
        ):
            urls = _get_video_urls(MagicMock(), 215)
            assert len(urls) == 2
            assert urls[0]["url"] == "https://a.com/1.mp4"

    def test_get_video_urls_empty(self):
        """環境変数未設定の場合"""
        from app.pipeline.sleeping_detector import _get_video_urls

        with patch.dict("os.environ", {}, clear=True):
            urls = _get_video_urls(MagicMock(), 215)
            assert len(urls) == 0


class TestRunnerIntegration:
    """パイプラインランナーとの統合テスト"""

    def test_sleeping_pipeline_registered(self):
        """sleepingパイプラインがランナーに登録されている"""
        from app.pipeline.runner import PIPELINES

        assert "sleeping" in PIPELINES

    def test_run_sleeping_no_urls(self, db):
        """動画URLがない場合は0を返す"""
        session = DietSession(id=1, session_number=215, kind="通常")
        db.add(session)
        db.commit()

        from app.pipeline.runner import run_sleeping

        with patch.dict("os.environ", {}, clear=True):
            count = run_sleeping(db, 215)
            assert count == 0
