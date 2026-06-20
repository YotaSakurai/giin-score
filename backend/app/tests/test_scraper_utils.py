"""スクレイパー・パイプラインのユーティリティ関数テスト

外部I/Oなしでテスト可能な純粋関数を網羅的にテスト。
"""

from unittest.mock import MagicMock

from bs4 import BeautifulSoup

from app.pipeline.member_profile_scraper import _normalize_shugiin_district
from app.pipeline.sangiin_scraper import (
    _clean_party_name,
    _extract_title_new,
    _extract_totals_new,
    _extract_vote_links,
    _parse_sanpilist_text,
)
from app.pipeline.shugiin_scraper import (
    _extract_bill_links,
    _normalize_status,
    _parse_sponsor_names,
)
from app.pipeline.utils import detect_encoding, health_check

# =====================================================================
# pipeline/utils.py
# =====================================================================


class TestDetectEncoding:
    def test_euc_jp(self):
        resp = MagicMock()
        resp.headers = {"content-type": "text/html; charset=euc-jp"}
        assert detect_encoding(resp) == "euc-jp"

    def test_shift_jis(self):
        resp = MagicMock()
        resp.headers = {
            "content-type": "text/html; charset=Shift_JIS"
        }
        assert detect_encoding(resp) == "shift_jis"

    def test_utf8_default(self):
        resp = MagicMock()
        resp.headers = {"content-type": "text/html"}
        assert detect_encoding(resp) == "utf-8"

    def test_missing_header(self):
        resp = MagicMock()
        resp.headers = {}
        assert detect_encoding(resp) == "utf-8"


class TestHealthCheck:
    def test_with_table(self):
        soup = BeautifulSoup("<html><table></table></html>", "html.parser")
        assert health_check(soup) is True

    def test_with_anchor(self):
        soup = BeautifulSoup(
            "<html><a href='#'>link</a></html>", "html.parser"
        )
        assert health_check(soup) is True

    def test_empty_div(self):
        soup = BeautifulSoup(
            "<html><div>text</div></html>", "html.parser"
        )
        assert health_check(soup) is False


# =====================================================================
# member_profile_scraper.py
# =====================================================================


class TestNormalizeShugiinDistrict:
    def test_hirei_paren(self):
        assert _normalize_shugiin_district("(比)北海道") == "比例北海道"

    def test_hirei_fullwidth_paren(self):
        assert (
            _normalize_shugiin_district("（比）北陸信越")
            == "比例北陸信越"
        )

    def test_small_district(self):
        assert _normalize_shugiin_district("東京1") == "東京1区"

    def test_large_number_district(self):
        assert _normalize_shugiin_district("北海道10") == "北海道10区"

    def test_already_normalized(self):
        assert _normalize_shugiin_district("東京5区") == "東京5区"

    def test_prefecture_only(self):
        result = _normalize_shugiin_district("大阪")
        assert result == "大阪"

    def test_empty(self):
        assert _normalize_shugiin_district("") == ""

    def test_unknown_format(self):
        assert _normalize_shugiin_district("unknown") == "unknown"


# =====================================================================
# sangiin_scraper.py
# =====================================================================


class TestExtractVoteLinks:
    def test_relative_links(self):
        html = (
            '<a href="213-0619-v001.htm">投票結果</a>'
            '<a href="213-0619-v002.htm">投票結果</a>'
        )
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_vote_links(
            soup, "https://example.com/base/vote.htm"
        )
        assert len(links) == 2
        assert links[0].endswith("213-0619-v001.htm")

    def test_absolute_links(self):
        html = '<a href="https://other.com/213-v001.htm">X</a>'
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_vote_links(
            soup, "https://example.com/base/"
        )
        assert len(links) == 1
        assert links[0] == "https://other.com/213-v001.htm"

    def test_root_relative_links(self):
        html = '<a href="/path/213-v001.htm">X</a>'
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_vote_links(
            soup, "https://example.com/base/"
        )
        assert len(links) == 1
        assert links[0].startswith("https://www.sangiin.go.jp")

    def test_deduplication(self):
        html = (
            '<a href="213-v001.htm">A</a>'
            '<a href="213-v001.htm">B</a>'
        )
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_vote_links(
            soup, "https://example.com/base/x.htm"
        )
        assert len(links) == 1

    def test_non_vote_links_excluded(self):
        html = (
            '<a href="other.htm">Other</a>'
            '<a href="213-0619-v001.htm">Vote</a>'
            '<a href="summary.html">Summary</a>'
        )
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_vote_links(
            soup, "https://example.com/base/x.htm"
        )
        assert len(links) == 1

    def test_no_links(self):
        soup = BeautifulSoup("<div>No links</div>", "html.parser")
        links = _extract_vote_links(
            soup, "https://example.com/"
        )
        assert len(links) == 0


class TestExtractTitleNew:
    def test_basic_title(self):
        html = (
            '<div id="ContentsBox">'
            '<dl class="ankenmei"><dd>民法改正法案</dd></dl>'
            '</div>'
        )
        soup = BeautifulSoup(html, "html.parser")
        contents = soup.find(id="ContentsBox")
        assert _extract_title_new(contents) == "民法改正法案"

    def test_removes_schedule_prefix(self):
        html = (
            '<div id="ContentsBox">'
            '<dl class="ankenmei">'
            '<dd>日程第1 民法改正法案</dd>'
            '</dl></div>'
        )
        soup = BeautifulSoup(html, "html.parser")
        contents = soup.find(id="ContentsBox")
        assert _extract_title_new(contents) == "民法改正法案"

    def test_removes_proposer_suffix(self):
        html = (
            '<div id="ContentsBox">'
            '<dl class="ankenmei">'
            '<dd>民法改正法案（内閣提出）</dd>'
            '</dl></div>'
        )
        soup = BeautifulSoup(html, "html.parser")
        contents = soup.find(id="ContentsBox")
        assert _extract_title_new(contents) == "民法改正法案"

    def test_no_ankenmei(self):
        html = '<div id="ContentsBox"><p>No title</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        contents = soup.find(id="ContentsBox")
        assert _extract_title_new(contents) == ""


class TestExtractTotalsNew:
    def test_basic(self):
        html = (
            '<div id="ContentsBox">'
            '<h3 class="tohyosousu">賛成票  112　反対票   5</h3>'
            '</div>'
        )
        soup = BeautifulSoup(html, "html.parser")
        contents = soup.find(id="ContentsBox")
        ayes, nays = _extract_totals_new(contents)
        assert ayes == 112
        assert nays == 5

    def test_zero_votes(self):
        html = (
            '<div id="ContentsBox">'
            '<h3 class="tohyosousu">賛成票  0　反対票   0</h3>'
            '</div>'
        )
        soup = BeautifulSoup(html, "html.parser")
        contents = soup.find(id="ContentsBox")
        ayes, nays = _extract_totals_new(contents)
        assert ayes == 0
        assert nays == 0

    def test_no_element(self):
        html = '<div id="ContentsBox"><p>No totals</p></div>'
        soup = BeautifulSoup(html, "html.parser")
        contents = soup.find(id="ContentsBox")
        ayes, nays = _extract_totals_new(contents)
        assert ayes == 0
        assert nays == 0


class TestParseSanpilistText:
    def test_basic(self):
        text = "賛成足立\u3000敏之賛成阿達\u3000雅志反対野田\u3000国義"
        records = _parse_sanpilist_text(text)
        assert len(records) == 3
        assert records[0][1] == "aye"
        assert records[1][1] == "aye"
        assert records[2][1] == "nay"

    def test_with_header(self):
        text = "賛成票 112　反対票 5賛成足立\u3000敏之"
        records = _parse_sanpilist_text(text)
        assert len(records) == 1
        assert records[0][1] == "aye"

    def test_abstain(self):
        text = "投票なし山田\u3000太郎"
        records = _parse_sanpilist_text(text)
        assert len(records) == 1
        assert records[0][1] == "abstain"

    def test_empty(self):
        assert _parse_sanpilist_text("") == []

    def test_short_name_filtered(self):
        """2文字未満の名前はフィルタされる。"""
        text = "賛成あ"
        records = _parse_sanpilist_text(text)
        assert len(records) == 0

    def test_mixed(self):
        text = (
            "賛成田中\u3000太郎"
            "反対鈴木\u3000花子"
            "投票なし山田\u3000一郎"
        )
        records = _parse_sanpilist_text(text)
        assert len(records) == 3
        votes = [r[1] for r in records]
        assert votes == ["aye", "nay", "abstain"]


class TestCleanPartyName:
    def test_removes_count(self):
        assert _clean_party_name("自由民主党(234名)") == "自由民主党"

    def test_fullwidth_parens(self):
        # 全角パーレンは半角パターンにマッチしない→そのまま返る
        result = _clean_party_name("立憲民主党（123名）")
        assert "立憲民主党" in result

    def test_no_parens(self):
        assert _clean_party_name("公明党") == "公明党"

    def test_empty(self):
        assert _clean_party_name("") == ""


# =====================================================================
# shugiin_scraper.py
# =====================================================================


class TestNormalizeStatus:
    def test_exact_matches(self):
        assert _normalize_status("成立") == "成立"
        assert _normalize_status("未了") == "廃案"
        assert _normalize_status("審議中") == "審議中"
        assert _normalize_status("本院議了") == "成立"

    def test_partial_matches(self):
        assert _normalize_status("修正可決") == "成立"
        assert _normalize_status("法案は可決されました") == "成立"
        assert _normalize_status("法案は否決されました") == "否決"
        assert _normalize_status("参議院で閉会中審査") == "継続"
        assert _normalize_status("法案が撤回された") == "撤回"

    def test_unknown(self):
        assert _normalize_status("不明なステータス") == "審議中"

    def test_empty(self):
        assert _normalize_status("") is None

    def test_whitespace(self):
        assert _normalize_status("   ") is None

    def test_whitespace_around(self):
        assert _normalize_status("  成立  ") == "成立"


class TestExtractBillLinks:
    def test_honbun_links(self):
        html = (
            '<a href="honbun/kaiji213_1.htm">本文</a>'
            '<a href="keika/kaiji213_1.htm">経過</a>'
        )
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_bill_links(
            soup, "https://example.com/bills/list.htm"
        )
        assert len(links) == 1
        assert "honbun" in links[0]

    def test_text_honbun(self):
        html = '<a href="detail.htm">本文</a>'
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_bill_links(
            soup, "https://example.com/"
        )
        assert len(links) == 1

    def test_deduplication(self):
        html = (
            '<a href="honbun/a.htm">A</a>'
            '<a href="honbun/a.htm">B</a>'
        )
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_bill_links(
            soup, "https://example.com/"
        )
        assert len(links) == 1

    def test_relative_url_resolved(self):
        html = '<a href="../honbun/a.htm">本文</a>'
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_bill_links(
            soup, "https://example.com/dir/list.htm"
        )
        assert len(links) == 1
        assert links[0].startswith("https://")

    def test_no_links(self):
        html = "<div>No bills</div>"
        soup = BeautifulSoup(html, "html.parser")
        links = _extract_bill_links(
            soup, "https://example.com/"
        )
        assert len(links) == 0


class TestParseSponsorNames:
    def test_comma_separated(self):
        result = _parse_sponsor_names("田中太郎、鈴木花子、山田一郎")
        assert result == ["田中太郎", "鈴木花子", "山田一郎"]

    def test_cabinet_returns_empty(self):
        assert _parse_sponsor_names("内閣") == []
        assert _parse_sponsor_names("内閣総理大臣") == []

    def test_short_names_filtered(self):
        result = _parse_sponsor_names("田中太郎、a、鈴木花子")
        assert "a" not in result
        assert len(result) == 2

    def test_empty(self):
        assert _parse_sponsor_names("") == []

    def test_fullwidth_space_separated(self):
        result = _parse_sponsor_names("田中太郎　鈴木花子")
        assert len(result) == 2
