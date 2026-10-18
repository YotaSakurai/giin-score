"""video_url_scraper のユニットテスト"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

from app.pipeline.video_url_scraper import (
    _estimate_sangiintv_start_sid,
    _estimate_shugiintv_start_id,
    _parse_japanese_date,
    _parse_shugiintv_date,
)


class TestParseShugiintvDate:
    def test_standard_url(self):
        url = (
            "http://hlsvod.shugiintv.go.jp/vod/_definst_/amlst:2026/2026-0717-1300-00/playlist.m3u8"
        )
        result = _parse_shugiintv_date(url)
        assert result == datetime(2026, 7, 17, 13, 0)

    def test_morning_session(self):
        url = (
            "http://hlsvod.shugiintv.go.jp/vod/_definst_/amlst:2026/2026-0305-0845-00/playlist.m3u8"
        )
        result = _parse_shugiintv_date(url)
        assert result == datetime(2026, 3, 5, 8, 45)

    def test_no_match(self):
        assert _parse_shugiintv_date("http://example.com/video.m3u8") is None


class TestParseJapaneseDate:
    def test_standard(self):
        assert _parse_japanese_date("2026年7月17日") == date(2026, 7, 17)

    def test_single_digit(self):
        assert _parse_japanese_date("2025年3月5日") == date(2025, 3, 5)

    def test_invalid(self):
        assert _parse_japanese_date("令和8年7月17日") is None

    def test_empty(self):
        assert _parse_japanese_date("") is None


class TestEstimateShugiintvStartId:
    def test_within_range(self):
        result = _estimate_shugiintv_start_id(date(2026, 1, 26))
        assert 56000 < result < 56200

    def test_before_all_anchors(self):
        result = _estimate_shugiintv_start_id(date(2024, 1, 1))
        assert result < 55800

    def test_after_all_anchors(self):
        result = _estimate_shugiintv_start_id(date(2027, 1, 1))
        assert result > 56386


class TestEstimateSangiintvStartSid:
    def test_within_range(self):
        result = _estimate_sangiintv_start_sid(date(2026, 1, 26))
        assert 8700 < result < 9100

    def test_before_all_anchors(self):
        result = _estimate_sangiintv_start_sid(date(2023, 1, 1))
        assert result < 8000

    def test_after_all_anchors(self):
        result = _estimate_sangiintv_start_sid(date(2027, 1, 1))
        assert result > 9000


class TestGetVideoUrlsForSession:
    @patch("app.pipeline.video_url_scraper._scan_shugiintv")
    @patch("app.pipeline.video_url_scraper._scan_sangiintv")
    @patch("app.pipeline.video_url_scraper._get_session_date_range")
    def test_returns_combined_results(self, mock_range, mock_sangiin, mock_shugiin):
        mock_range.return_value = (date(2026, 1, 26), date(2026, 7, 25))
        mock_shugiin.return_value = [
            {
                "url": "https://shugiintv.go.jp/jp/index.php?ex=VL&deli_id=56100",
                "meeting_name": "予算委員会",
                "date": datetime(2026, 3, 5),
                "chamber": "shugiin",
                "source_id": "shugiin_56100",
            }
        ]
        mock_sangiin.return_value = [
            {
                "url": "https://webtv.sangiin.go.jp/webtv/detail.php?sid=9000",
                "meeting_name": "本会議",
                "date": datetime(2026, 5, 13),
                "chamber": "sangiin",
                "source_id": "sangiin_9000",
            }
        ]

        from app.pipeline.video_url_scraper import get_video_urls_for_session

        db = MagicMock()
        results = get_video_urls_for_session(db, 221)
        assert len(results) == 2
        assert results[0]["chamber"] == "shugiin"
        assert results[1]["chamber"] == "sangiin"

    @patch("app.pipeline.video_url_scraper._get_session_date_range")
    def test_returns_empty_when_no_date_range(self, mock_range):
        mock_range.return_value = None

        from app.pipeline.video_url_scraper import get_video_urls_for_session

        db = MagicMock()
        results = get_video_urls_for_session(db, 999)
        assert results == []
