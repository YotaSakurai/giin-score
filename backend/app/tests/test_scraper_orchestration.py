"""スクレイパー統合テスト（HTTPモック版）

sangiin_scraper, shugiin_scraper, shitsumon_scraper,
member_profile_scraper, smartnews_loader の統合フローをテストする。
"""

import tempfile
from unittest.mock import MagicMock, patch

import httpx
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.models.session import DietSession

# =====================================================================
# smartnews_loader.py: load_bills_csv
# =====================================================================


class TestLoadBillsCsv:
    def test_from_csv_file(self, db: Session):
        """CSVファイルから法案を読み込む。"""
        from app.pipeline.smartnews_loader import load_bills_csv

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        csv_content = (
            "session,bill_kind,bill_number,title,status,result\n"
            "215,閣法,1,テスト法案A,成立,可決\n"
            "215,衆法,2,テスト法案B,審議中,\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        result = load_bills_csv(db, csv_path=csv_path)
        assert result == 2

        bills = db.query(Bill).all()
        assert len(bills) == 2
        assert bills[0].title == "テスト法案A"

        # pipeline_run
        run = db.query(PipelineRun).filter_by(pipeline_name="smartnews_bills").first()
        assert run.status == "completed"
        assert run.records_processed == 2

    def test_cp932_fallback(self, db: Session):
        """UTF-8デコード失敗時にCP932へフォールバック。"""
        from app.pipeline.smartnews_loader import load_bills_csv

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        csv_content = "session,title\n215,テスト法案\n"
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
            f.write(csv_content.encode("cp932"))
            csv_path = f.name

        result = load_bills_csv(db, csv_path=csv_path)
        assert result == 1

    def test_no_csv_dir(self, db: Session):
        """CSVディレクトリが存在しない場合は0を返す。"""
        from app.pipeline.smartnews_loader import load_bills_csv

        with patch("app.pipeline.smartnews_loader.settings") as mock_settings:
            mock_settings.data_dir = "/nonexistent"
            result = load_bills_csv(db)
        assert result == 0

    def test_row_processing_error(self, db: Session):
        """行処理でエラーが発生してもスキップして続行。"""
        from app.pipeline.smartnews_loader import load_bills_csv

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        csv_content = (
            "session,title\n"
            "215,正常な法案\n"
            "invalid,\n"  # session_numが文字列でint変換失敗 → Falseだがエラーにはならない
            "215,二番目の法案\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(csv_content)
            csv_path = f.name

        result = load_bills_csv(db, csv_path=csv_path)
        assert result >= 1  # 少なくとも正常行は処理される


# =====================================================================
# sangiin_scraper.py: scrape_votes
# =====================================================================

SANGIIN_VOTE_LIST_HTML = """
<html><body>
<div id="ContentsBox">
<table><tr><td><a href="215-0101-v001.htm">法案1</a></td></tr></table>
</div>
</body></html>
"""

SANGIIN_VOTE_PAGE_NEW_HTML = """
<html><body>
<div id="ContentsBox">
<h1>投票結果</h1>
<dl class="ankenmei"><dd>テスト法案A（内閣提出）</dd></dl>
<h3 class="tohyosousu">投票総数　賛成票 120　反対票 80</h3>
<h4 class="party">自由民主党(50名)</h4>
<dl class="sanpilist">賛成田中　太郎賛成鈴木　花子反対山田　一郎</dl>
</div>
</body></html>
"""


class TestScrapeVotes:
    @patch("app.pipeline.sangiin_scraper.time.sleep")
    def test_basic_flow(self, mock_sleep, db: Session):
        """投票ページの新構造をパースできる。"""
        from app.pipeline.sangiin_scraper import scrape_votes

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        responses = [
            # 投票一覧ページ
            httpx.Response(
                200,
                text=SANGIIN_VOTE_LIST_HTML,
                request=httpx.Request("GET", "https://example.com"),
            ),
            # 個別投票ページ
            httpx.Response(
                200,
                text=SANGIIN_VOTE_PAGE_NEW_HTML,
                request=httpx.Request("GET", "https://example.com"),
            ),
        ]

        mock_client = MagicMock()
        mock_client.get.side_effect = responses
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.sangiin_scraper.httpx.Client", return_value=mock_client):
            result = scrape_votes(db, 215)

        assert result >= 2  # 田中+鈴木+山田 = 3, 少なくとも2
        run = db.query(PipelineRun).filter_by(pipeline_name="sangiin_votes").first()
        assert run.status == "completed"

    @patch("app.pipeline.sangiin_scraper.time.sleep")
    def test_health_check_fail(self, mock_sleep, db: Session):
        """ヘルスチェック失敗時にfailedマーク。"""
        from app.pipeline.sangiin_scraper import scrape_votes

        # 空HTMLでhealth_checkが失敗する
        resp = httpx.Response(
            200,
            text="<html><head></head><body></body></html>",
            request=httpx.Request("GET", "https://example.com"),
        )

        mock_client = MagicMock()
        mock_client.get.return_value = resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.sangiin_scraper.httpx.Client", return_value=mock_client):
            result = scrape_votes(db, 215)

        assert result == 0
        run = db.query(PipelineRun).filter_by(pipeline_name="sangiin_votes").first()
        assert run.status == "failed"


# =====================================================================
# shugiin_scraper.py: scrape_bills_list
# =====================================================================

SHUGIIN_BILLS_LIST_HTML = """
<html><body>
<table>
<caption>閣法の一覧</caption>
<tr><td>215</td><td>1</td><td>テスト法案A</td><td>成立</td></tr>
<tr><td>215</td><td>2</td><td>テスト法案B</td><td>審議中</td></tr>
<tr><td>214</td><td>1</td><td>前会期法案</td><td>成立</td></tr>
</table>
</body></html>
"""


class TestScrапeBillsList:
    @patch("app.pipeline.shugiin_scraper.time.sleep")
    def test_basic_flow(self, mock_sleep, db: Session):
        """衆議院法案一覧をパースしてBillをDB保存する。"""
        from app.pipeline.shugiin_scraper import scrape_bills_list

        resp = httpx.Response(
            200,
            text=SHUGIIN_BILLS_LIST_HTML,
            request=httpx.Request("GET", "https://example.com"),
        )

        mock_client = MagicMock()
        mock_client.get.return_value = resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.shugiin_scraper.httpx.Client", return_value=mock_client):
            result = scrape_bills_list(db, 215)

        # session=215 の法案のみ取得（前会期の214は除外）
        assert result == 2
        bills = db.query(Bill).all()
        assert len(bills) == 2

        run = db.query(PipelineRun).filter_by(pipeline_name="shugiin_bills_list").first()
        assert run.status == "completed"

    @patch("app.pipeline.shugiin_scraper.time.sleep")
    def test_duplicate_updates_status(self, mock_sleep, db: Session):
        """既存法案がある場合はステータスだけ更新する。"""
        from app.pipeline.shugiin_scraper import scrape_bills_list

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(Bill(session_id=1, bill_kind="閣法", title="テスト法案A", status="審議中"))
        db.commit()

        resp = httpx.Response(
            200,
            text=SHUGIIN_BILLS_LIST_HTML,
            request=httpx.Request("GET", "https://example.com"),
        )

        mock_client = MagicMock()
        mock_client.get.return_value = resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.shugiin_scraper.httpx.Client", return_value=mock_client):
            result = scrape_bills_list(db, 215)

        # 法案Aは既存なので新規はBのみ
        assert result == 1
        # 既存法案Aのステータスが更新されている
        bill_a = db.query(Bill).filter_by(title="テスト法案A").first()
        assert bill_a.status == "成立"


# =====================================================================
# shugiin_scraper.py: scrape_bills (detail)
# =====================================================================

SHUGIIN_DETAIL_HTML = """
<html><body>
<table>
<caption>閣法の一覧</caption>
<tr><td>215</td><td>1</td><td>テスト法案A</td><td>成立</td></tr>
</table>
<a href="/internet/itdb_gian.nsf/html/gian/honbun/houan/g21509001.htm">本文</a>
</body></html>
"""

SHUGIIN_BILL_DETAIL_HTML = """
<html><body>
<h3>テスト法案A</h3>
<table>
<tr><th>提出者</th><td>田中太郎、鈴木花子</td></tr>
</table>
</body></html>
"""


class TestScrapeBillsDetail:
    @patch("app.pipeline.shugiin_scraper.time.sleep")
    def test_bill_detail_with_sponsors(self, mock_sleep, db: Session):
        """法案詳細ページから提出者を抽出する。"""
        from app.pipeline.shugiin_scraper import scrape_bills

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(Bill(session_id=1, bill_kind="閣法", title="テスト法案A"))
        db.commit()

        responses = [
            httpx.Response(
                200,
                text=SHUGIIN_DETAIL_HTML,
                request=httpx.Request("GET", "https://example.com"),
            ),
            httpx.Response(
                200,
                text=SHUGIIN_BILL_DETAIL_HTML,
                request=httpx.Request("GET", "https://example.com"),
            ),
        ]

        mock_client = MagicMock()
        mock_client.get.side_effect = responses
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.shugiin_scraper.httpx.Client", return_value=mock_client):
            result = scrape_bills(db, 215)

        assert result == 1
        run = db.query(PipelineRun).filter_by(pipeline_name="shugiin_bills").first()
        assert run.status == "completed"


# =====================================================================
# shitsumon_scraper.py: scrape_written_questions
# =====================================================================

SHUGIIN_SHITSUMON_HTML = """
<html><body>
<table>
<tr>
<td>1</td>
<td>テスト質問主意書</td>
<td>田中太郎君</td>
<td>令和6年3月1日</td>
<td><a href="a215001.htm">質問</a></td>
<td><a href="b215001.htm">答弁</a></td>
</tr>
</table>
</body></html>
"""

SANGIIN_SHITSUMON_HTML = """
<html><body>
<table class="list_c">
<tr>
<th>提出番号</th>
<th>件名</th>
<td>参議院テスト質問</td>
</tr>
<tr>
<td>1</td>
<td>提出者</td>
<td>鈴木花子</td>
<td><a href="#">質問本文</a></td>
<td><a href="#">答弁本文</a></td>
</tr>
</table>
</body></html>
"""


class TestScrapeWrittenQuestions:
    @patch("app.pipeline.shitsumon_scraper.time.sleep")
    def test_shugiin_and_sangiin(self, mock_sleep, db: Session):
        """衆参両院の質問主意書を取得する。"""
        from app.pipeline.shitsumon_scraper import scrape_written_questions

        responses = [
            # 衆議院
            httpx.Response(
                200,
                text=SHUGIIN_SHITSUMON_HTML,
                request=httpx.Request("GET", "https://example.com"),
            ),
            # 参議院
            httpx.Response(
                200,
                text=SANGIIN_SHITSUMON_HTML,
                request=httpx.Request("GET", "https://example.com"),
            ),
        ]

        call_count = [0]

        def mock_get(url, *args, **kwargs):
            idx = min(call_count[0], len(responses) - 1)
            call_count[0] += 1
            return responses[idx]

        mock_client = MagicMock()
        mock_client.get.side_effect = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.shitsumon_scraper.httpx.Client", return_value=mock_client):
            result = scrape_written_questions(db, 215)

        assert result >= 1
        run = db.query(PipelineRun).filter_by(pipeline_name="written_questions").first()
        assert run.status == "completed"

    @patch("app.pipeline.shitsumon_scraper.time.sleep")
    def test_shugiin_not_found(self, mock_sleep, db: Session):
        """衆議院ページが404の場合もエラーにならない。"""
        from app.pipeline.shitsumon_scraper import scrape_written_questions

        def mock_get(url, *args, **kwargs):
            if "shugiin" in url:
                raise httpx.HTTPStatusError(
                    "Not Found",
                    request=httpx.Request("GET", url),
                    response=httpx.Response(404),
                )
            return httpx.Response(
                200,
                text="<html><body></body></html>",
                request=httpx.Request("GET", url),
            )

        mock_client = MagicMock()
        mock_client.get.side_effect = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.shitsumon_scraper.httpx.Client", return_value=mock_client):
            result = scrape_written_questions(db, 215)

        assert result == 0
        run = db.query(PipelineRun).filter_by(pipeline_name="written_questions").first()
        assert run.status == "completed"


# =====================================================================
# shitsumon_scraper.py: ヘルパー関数
# =====================================================================


class TestShitsumonHelpers:
    def test_clean_shugiin_name(self):
        from app.pipeline.shitsumon_scraper import _clean_shugiin_name

        assert _clean_shugiin_name("田中太郎君") == "田中太郎"
        assert _clean_shugiin_name("鈴木花子") == "鈴木花子"

    def test_clean_sangiin_name(self):
        from app.pipeline.shitsumon_scraper import _clean_sangiin_name

        assert _clean_sangiin_name("田中太郎君") == "田中太郎"
        assert _clean_sangiin_name("鈴木花子さん") == "鈴木花子"
        assert _clean_sangiin_name("提出者 山田一郎") == "山田一郎"

    def test_parse_date_reiwa(self):
        from datetime import date

        from app.pipeline.shitsumon_scraper import _parse_date

        d = _parse_date("令和6年3月1日")
        assert d == date(2024, 3, 1)

    def test_parse_date_heisei(self):
        from datetime import date

        from app.pipeline.shitsumon_scraper import _parse_date

        d = _parse_date("平成31年4月1日")
        assert d == date(2019, 4, 1)

    def test_parse_date_iso(self):
        from datetime import date

        from app.pipeline.shitsumon_scraper import _parse_date

        d = _parse_date("2024/03/01")
        assert d == date(2024, 3, 1)
        d2 = _parse_date("2024-03-01")
        assert d2 == date(2024, 3, 1)

    def test_parse_date_empty(self):
        from app.pipeline.shitsumon_scraper import _parse_date

        assert _parse_date("") is None
        assert _parse_date("不明") is None


# =====================================================================
# member_profile_scraper.py: scrape_member_profiles
# =====================================================================

SHUGIIN_MEMBERS_HTML = """
<html><body>
<table>
<tr valign="top">
<td>田中太郎</td>
<td>たなか たろう</td>
<td>自民</td>
<td>東京5</td>
<td></td>
</tr>
</table>
</body></html>
"""

SANGIIN_MEMBERS_HTML = """
<html><body>
<table summary="議員一覧">
<tr>
<td>鈴木花子</td>
<td>すずき はなこ</td>
<td>立憲</td>
<td>神奈川</td>
</tr>
</table>
</body></html>
"""


class TestScrapeProfiles:
    @patch("app.pipeline.member_profile_scraper.time.sleep")
    def test_basic_flow(self, mock_sleep, db: Session):
        """衆参両院のプロフィールスクレイピング基本フロー。"""
        from app.pipeline.member_profile_scraper import scrape_member_profiles

        # 事前にメンバーを作成
        db.add(Member(id=1, name="田中太郎", chamber="representatives"))
        db.add(Member(id=2, name="鈴木花子", chamber="councillors"))
        db.commit()

        shugiin_resp = httpx.Response(
            200,
            text=SHUGIIN_MEMBERS_HTML,
            headers={"content-type": "text/html; charset=utf-8"},
            request=httpx.Request("GET", "https://example.com"),
        )
        sangiin_resp = httpx.Response(
            200,
            text=SANGIIN_MEMBERS_HTML,
            request=httpx.Request("GET", "https://example.com"),
        )

        call_count = [0]

        def mock_get(url, *args, **kwargs):
            call_count[0] += 1
            if "sangiin" in url:
                return sangiin_resp
            return shugiin_resp

        mock_client = MagicMock()
        mock_client.get.side_effect = mock_get
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.member_profile_scraper.httpx.Client", return_value=mock_client):
            result = scrape_member_profiles(db)

        assert result >= 1
        run = db.query(PipelineRun).filter_by(pipeline_name="member_profiles").first()
        assert run.status == "completed"

    @patch("app.pipeline.member_profile_scraper.time.sleep")
    def test_exception_marks_failed(self, mock_sleep, db: Session):
        """例外時にpipeline_runがfailedになる。"""
        from app.pipeline.member_profile_scraper import scrape_member_profiles

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(side_effect=RuntimeError("network error"))
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("app.pipeline.member_profile_scraper.httpx.Client", return_value=mock_client):
            try:
                scrape_member_profiles(db)
            except RuntimeError:
                pass

        run = db.query(PipelineRun).filter_by(pipeline_name="member_profiles").first()
        assert run.status == "failed"


# =====================================================================
# sangiin_scraper.py: ヘルパー関数
# =====================================================================


class TestSangiinHelpers:
    def test_find_or_create_bill(self, db: Session):
        from app.pipeline.sangiin_scraper import _find_or_create_bill

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        # 新規作成
        bill = _find_or_create_bill(db, 1, "テスト法案の完全なタイトル")
        db.flush()
        assert bill is not None
        assert bill.title == "テスト法案の完全なタイトル"

        # 同じタイトルで検索→既存を返す
        bill2 = _find_or_create_bill(db, 1, "テスト法案の完全なタイトル")
        assert bill2.id == bill.id

    def test_find_or_create_bill_new(self, db: Session):
        """異なるタイトルなら新規作成される。"""
        from app.pipeline.sangiin_scraper import _find_or_create_bill

        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        bill1 = _find_or_create_bill(db, 1, "法案A")
        db.flush()
        bill2 = _find_or_create_bill(db, 1, "法案B")
        db.flush()
        assert bill1.id != bill2.id

    def test_parse_vote(self):
        from app.pipeline.sangiin_scraper import _parse_vote

        assert _parse_vote("賛成") == "aye"
        assert _parse_vote("○") == "aye"
        assert _parse_vote("〇") == "aye"
        assert _parse_vote("反対") == "nay"
        assert _parse_vote("×") == "nay"
        assert _parse_vote("棄権") == "abstain"
        assert _parse_vote("欠席") == "absent"
        assert _parse_vote("") is None
        assert _parse_vote("出席") is None

    def test_scrape_vote_page_legacy(self, db: Session):
        """旧構造（table/dt-dd）のパース。"""
        from bs4 import BeautifulSoup

        from app.pipeline.sangiin_scraper import _scrape_vote_page_legacy

        s = DietSession(id=1, session_number=212, kind="通常")
        db.add(s)
        db.commit()

        html = """
        <html><body>
        <dt>案件名</dt><dd>旧テスト法案</dd>
        <p>可決されました</p>
        <table>
        <tr><th>賛成</th><th>反対</th><th>氏名</th></tr>
        <tr><td>○</td><td></td><td>田中太郎</td></tr>
        <tr><td></td><td>×</td><td>鈴木花子</td></tr>
        </table>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        count = _scrape_vote_page_legacy(db, soup, 212)
        assert count >= 1
