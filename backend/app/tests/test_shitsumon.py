"""質問主意書関連のテスト"""

from datetime import date

from app.pipeline.shitsumon_scraper import (
    _clean_sangiin_name,
    _clean_shugiin_name,
    _parse_date,
)


class TestCleanNames:
    def test_shugiin_removes_kun(self):
        assert _clean_shugiin_name("山井和則君") == "山井和則"

    def test_shugiin_no_suffix(self):
        assert _clean_shugiin_name("山井和則") == "山井和則"

    def test_sangiin_removes_kun(self):
        assert _clean_sangiin_name("西田　　実仁君") == "西田　　実仁"

    def test_sangiin_removes_san(self):
        assert _clean_sangiin_name("田中花子さん") == "田中花子"

    def test_sangiin_removes_proposer_label(self):
        assert _clean_sangiin_name("提出者 西田実仁君") == "西田実仁"


class TestParseDate:
    def test_reiwa(self):
        assert _parse_date("令和6年1月27日") == date(2024, 1, 27)

    def test_heisei(self):
        assert _parse_date("平成31年3月15日") == date(2019, 3, 15)

    def test_iso_format(self):
        assert _parse_date("2024-01-27") == date(2024, 1, 27)

    def test_slash_format(self):
        assert _parse_date("2024/01/27") == date(2024, 1, 27)

    def test_empty(self):
        assert _parse_date("") is None

    def test_invalid(self):
        assert _parse_date("no date here") is None
