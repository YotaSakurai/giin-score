"""API層の網羅テスト

未カバーだったエンドポイントを中心にテスト。
リアルSQLiteを使い、モックなしでAPI→DB→レスポンスの全フローを検証する。
"""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.bill import Bill, BillSponsor
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.models.score import MemberScore
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.models.vote import VoteRecord, VoteResult
from app.models.written_question import WrittenQuestion


@pytest.fixture()
def rich_seed(db: Session):
    """API網羅テスト用のリッチなシードデータ。

    - 2つの会期 (215, 216)
    - 5名の議員 (衆院3/参院2、3政党、2選挙区パターン)
    - 両会期分のスコア (movers テスト用)
    - 発言、法案、投票記録、質問品質、質問主意書、パイプライン実行記録
    """
    s1 = DietSession(id=1, session_number=215, kind="通常")
    s2 = DietSession(id=2, session_number=216, kind="臨時")
    db.add_all([s1, s2])
    db.flush()

    members = [
        Member(
            id=1, name="田中太郎", chamber="representatives",
            party="自由民主党", district="東京1区",
            role_category="ruling_junior",
        ),
        Member(
            id=2, name="鈴木花子", chamber="councillors",
            party="立憲民主党", district="東京都",
            role_category="opposition_senior",
        ),
        Member(
            id=3, name="山田一郎", chamber="representatives",
            party="自由民主党", district="大阪1区",
            role_category="ruling_junior",
        ),
        Member(
            id=4, name="佐藤次郎", chamber="councillors",
            party="日本維新の会", district="大阪府",
            role_category="opposition_junior",
        ),
        Member(
            id=5, name="高橋三郎", chamber="representatives",
            party="立憲民主党", district="東京2区",
            role_category="opposition_junior",
        ),
    ]
    db.add_all(members)
    db.flush()

    # --- 会期215のスコア ---
    scores_215 = [
        MemberScore(
            member_id=1, session_id=1,
            legislative_activity=80, voting_behavior=70,
            policy_influence=60, transparency=50,
            question_quality=90, total=72, grade="B",
        ),
        MemberScore(
            member_id=2, session_id=1,
            legislative_activity=90, voting_behavior=85,
            policy_influence=80, transparency=75,
            question_quality=95, total=86, grade="A",
        ),
        MemberScore(
            member_id=3, session_id=1,
            legislative_activity=30, voting_behavior=25,
            policy_influence=20, transparency=15,
            question_quality=10, total=22, grade="D",
        ),
        MemberScore(
            member_id=4, session_id=1,
            legislative_activity=50, voting_behavior=55,
            policy_influence=45, transparency=40,
            question_quality=60, total=50, grade="C",
        ),
    ]
    db.add_all(scores_215)

    # --- 会期216のスコア (変動あり) ---
    scores_216 = [
        MemberScore(
            member_id=1, session_id=2,
            legislative_activity=85, voting_behavior=75,
            policy_influence=65, transparency=55,
            question_quality=92, total=76, grade="B",
        ),
        MemberScore(
            member_id=2, session_id=2,
            legislative_activity=70, voting_behavior=60,
            policy_influence=55, transparency=50,
            question_quality=65, total=60, grade="B",
        ),
        MemberScore(
            member_id=3, session_id=2,
            legislative_activity=50, voting_behavior=45,
            policy_influence=40, transparency=35,
            question_quality=30, total=42, grade="C",
        ),
    ]
    db.add_all(scores_216)
    db.flush()

    # --- 発言 ---
    speeches = [
        Speech(
            id=1, session_id=1, member_id=1,
            meeting_name="予算委員会",
            speech_date=date(2024, 2, 15),
            speech_chars=500,
            speech_url="https://example.com/s1",
        ),
        Speech(
            id=2, session_id=1, member_id=1,
            meeting_name="厚生労働委員会",
            speech_date=date(2024, 3, 1),
            speech_chars=300,
        ),
        Speech(
            id=3, session_id=1, member_id=2,
            meeting_name="予算委員会",
            speech_date=date(2024, 2, 20),
            speech_chars=800,
        ),
    ]
    db.add_all(speeches)
    db.flush()

    # --- 質問品質スコア ---
    quality_scores = [
        SpeechQualityScore(
            speech_id=1, member_id=1, session_id=1,
            policy_relevance=80, constructiveness=70,
            expertise=60, national_interest=75,
            overall_quality=71.3,
            analysis_summary="政策提言を含む建設的な質問",
        ),
        SpeechQualityScore(
            speech_id=3, member_id=2, session_id=1,
            policy_relevance=90, constructiveness=85,
            expertise=80, national_interest=88,
            overall_quality=85.8,
            analysis_summary="専門的なデータ分析に基づく追及",
        ),
    ]
    db.add_all(quality_scores)

    # --- 法案 ---
    bills = [
        Bill(
            id=1, session_id=1, bill_kind="閣法",
            bill_number="1", title="予算関連法案",
            status="成立", result="可決",
            proposer_type="cabinet",
        ),
        Bill(
            id=2, session_id=1, bill_kind="衆法",
            bill_number="5", title="教育基本法改正案",
            status="審議中", proposer_type="member",
        ),
        Bill(
            id=3, session_id=1, bill_kind="参法",
            bill_number="3", title="環境保護法案",
            status="否決", result="否決",
            proposer_type="member",
        ),
    ]
    db.add_all(bills)
    db.flush()

    # --- 法案提出者 ---
    sponsors = [
        BillSponsor(bill_id=2, member_id=1, sponsor_type="primary"),
        BillSponsor(bill_id=2, member_id=3, sponsor_type="co-sponsor"),
        BillSponsor(bill_id=3, member_id=2, sponsor_type="primary"),
    ]
    db.add_all(sponsors)

    # --- 投票結果・記録 ---
    vr1 = VoteResult(
        id=1, bill_id=1, chamber="representatives",
        ayes=250, nays=100, result="可決",
    )
    vr2 = VoteResult(
        id=2, bill_id=1, chamber="councillors",
        ayes=140, nays=80, result="可決",
    )
    db.add_all([vr1, vr2])
    db.flush()

    vote_records = [
        VoteRecord(vote_result_id=1, member_id=1, vote="aye"),
        VoteRecord(vote_result_id=1, member_id=3, vote="aye"),
        VoteRecord(vote_result_id=1, member_id=5, vote="nay"),
        VoteRecord(vote_result_id=2, member_id=2, vote="nay"),
        VoteRecord(vote_result_id=2, member_id=4, vote="aye"),
    ]
    db.add_all(vote_records)

    # --- 質問主意書 ---
    wqs = [
        WrittenQuestion(
            session_id=1, member_id=1, chamber="representatives",
            question_number=1, title="少子化対策に関する質問主意書",
            submitted_date=date(2024, 2, 1),
            answer_date=date(2024, 2, 15),
            has_answer=True,
        ),
        WrittenQuestion(
            session_id=1, member_id=1, chamber="representatives",
            question_number=2, title="防衛費に関する質問主意書",
            submitted_date=date(2024, 3, 1),
            has_answer=False,
        ),
        WrittenQuestion(
            session_id=1, member_id=2, chamber="councillors",
            question_number=1, title="年金制度に関する質問主意書",
            submitted_date=date(2024, 2, 10),
            has_answer=False,
        ),
    ]
    db.add_all(wqs)

    # --- パイプライン実行記録 ---
    runs = [
        PipelineRun(
            pipeline_name="members", session_number=215,
            status="completed",
            started_at=datetime(2024, 1, 1, tzinfo=UTC),
            finished_at=datetime(2024, 1, 1, 1, 0, tzinfo=UTC),
            records_processed=500,
        ),
        PipelineRun(
            pipeline_name="speeches", session_number=215,
            status="completed",
            started_at=datetime(2024, 1, 2, tzinfo=UTC),
            finished_at=datetime(2024, 1, 2, 2, 0, tzinfo=UTC),
            records_processed=3000,
        ),
        PipelineRun(
            pipeline_name="scoring", session_number=215,
            status="failed",
            started_at=datetime(2024, 1, 3, tzinfo=UTC),
            finished_at=datetime(2024, 1, 3, 0, 30, tzinfo=UTC),
            records_processed=0,
            error_message="DB connection lost",
        ),
    ]
    db.add_all(runs)
    db.commit()


# =====================================================================
# Members API
# =====================================================================


class TestMembersDistricts:
    def test_districts_all(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/districts")
        assert resp.status_code == 200
        districts = resp.json()
        assert isinstance(districts, list)
        assert "東京1区" in districts
        assert "大阪1区" in districts

    def test_districts_filter_chamber(self, client: TestClient, rich_seed):
        resp = client.get(
            "/api/v1/members/districts?chamber=councillors"
        )
        assert resp.status_code == 200
        districts = resp.json()
        assert "東京都" in districts
        # 衆院の選挙区は含まれない
        assert "東京1区" not in districts


class TestMembersRoleCategories:
    def test_role_categories_all(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/role-categories")
        assert resp.status_code == 200
        cats = resp.json()
        assert "ruling_junior" in cats
        assert "opposition_senior" in cats

    def test_role_categories_filter_chamber(
        self, client: TestClient, rich_seed
    ):
        resp = client.get(
            "/api/v1/members/role-categories?chamber=councillors"
        )
        assert resp.status_code == 200
        cats = resp.json()
        assert "opposition_senior" in cats
        assert "ruling_junior" not in cats


class TestMembersSimilar:
    def test_similar_members(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/1/similar?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 3
        # member 1 自身は含まれない
        ids = [m["id"] for m in data]
        assert 1 not in ids

    def test_similar_member_not_found(
        self, client: TestClient, rich_seed
    ):
        # member 5 はスコアなし
        resp = client.get("/api/v1/members/5/similar")
        assert resp.status_code == 404

    def test_similar_nonexistent_member(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/999/similar")
        assert resp.status_code == 404


class TestMembersSpeeches:
    def test_speeches_list(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/1/speeches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        # 日付降順
        if data["items"][0]["speech_date"] and data["items"][1]["speech_date"]:
            assert (
                data["items"][0]["speech_date"]
                >= data["items"][1]["speech_date"]
            )

    def test_speeches_pagination(self, client: TestClient, rich_seed):
        resp = client.get(
            "/api/v1/members/1/speeches?per_page=1&page=2"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["pages"] == 2

    def test_speeches_member_not_found(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/999/speeches")
        assert resp.status_code == 404

    def test_speeches_empty(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/4/speeches")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestMembersVotes:
    def test_votes_list(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/1/votes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["vote"] == "aye"
        assert item["member_name"] == "田中太郎"

    def test_votes_with_bill_title(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/1/votes")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["bill_title"] == "予算関連法案"

    def test_votes_member_not_found(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/999/votes")
        assert resp.status_code == 404


class TestMembersSpeechQuality:
    def test_speech_quality_list(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/1/speech-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["policy_relevance"] == 80
        assert item["overall_quality"] == 71.3
        assert "政策提言" in item["analysis_summary"]

    def test_speech_quality_empty(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/3/speech-quality")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_speech_quality_member_not_found(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/999/speech-quality")
        assert resp.status_code == 404


class TestMembersVotePattern:
    def test_vote_pattern(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/members/1/vote-pattern")
        assert resp.status_code == 200
        data = resp.json()
        assert data["member_id"] == 1
        assert data["total_votes"] >= 1
        assert 0 <= data["dissent_rate"] <= 100
        assert 0 <= data["participation_rate"] <= 100

    def test_vote_pattern_with_dissent(
        self, client: TestClient, rich_seed
    ):
        """member 5 (立憲) は nay だが同党 member 2 は参院なので
        衆院同党員なし→造反判定なし。"""
        resp = client.get("/api/v1/members/5/vote-pattern")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_votes"] == 1

    def test_vote_pattern_no_votes(
        self, client: TestClient, rich_seed
    ):
        """投票記録がない議員。"""
        resp = client.get("/api/v1/members/3/vote-pattern")
        # member 3 は vr1 で aye → 記録あり
        assert resp.status_code == 200

    def test_vote_pattern_member_not_found(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/999/vote-pattern")
        assert resp.status_code == 404


class TestMembersWrittenQuestions:
    def test_written_questions_list(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/1/written-questions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        # 各項目のフィールドチェック
        item = data["items"][0]
        assert "title" in item
        assert "has_answer" in item

    def test_written_questions_pagination(
        self, client: TestClient, rich_seed
    ):
        resp = client.get(
            "/api/v1/members/1/written-questions?per_page=1"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pages"] == 2
        assert len(data["items"]) == 1

    def test_written_questions_empty(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/3/written-questions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_written_questions_member_not_found(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/members/999/written-questions")
        assert resp.status_code == 404


# =====================================================================
# Scores API
# =====================================================================


class TestScoresCSVExport:
    def test_csv_export(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/scores/export/csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers["content-disposition"]
        body = resp.text
        # BOM付きUTF-8のヘッダー行
        assert "議員名" in body
        assert "グレード" in body
        # データ行がある
        assert "田中太郎" in body

    def test_csv_export_filter_chamber(
        self, client: TestClient, rich_seed
    ):
        resp = client.get(
            "/api/v1/scores/export/csv?chamber=councillors"
        )
        assert resp.status_code == 200
        body = resp.text
        assert "鈴木花子" in body
        assert "田中太郎" not in body

    def test_csv_export_filter_party(
        self, client: TestClient, rich_seed
    ):
        resp = client.get(
            "/api/v1/scores/export/csv?party=自由民主党"
        )
        assert resp.status_code == 200
        body = resp.text
        assert "田中太郎" in body
        assert "鈴木花子" not in body


class TestScoresPartyTrend:
    def test_party_trend(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/scores/party-trend")
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 2
        # 会期番号昇順
        assert data["sessions"][0]["session_number"] == 215
        assert data["sessions"][1]["session_number"] == 216
        # 政党データあり
        s215 = data["sessions"][0]["parties"]
        assert "自由民主党" in s215

    def test_party_trend_filter_chamber(
        self, client: TestClient, rich_seed
    ):
        resp = client.get(
            "/api/v1/scores/party-trend?chamber=representatives"
        )
        assert resp.status_code == 200
        data = resp.json()
        # 参院のみの維新は会期215には含まれない
        s215 = data["sessions"][0]["parties"]
        assert "日本維新の会" not in s215


class TestScoresMovers:
    def test_movers(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/scores/movers")
        assert resp.status_code == 200
        data = resp.json()
        assert "risers" in data
        assert "fallers" in data
        # member 1: 72→76 (+4), member 3: 22→42 (+20)
        # member 2: 86→60 (-26)
        risers = data["risers"]
        fallers = data["fallers"]
        assert len(risers) > 0
        assert len(fallers) > 0
        # 最大上昇者は member 3 (+20)
        top_riser = risers[0]
        assert top_riser["diff"] > 0
        # 最大下降者は member 2 (-26)
        top_faller = fallers[0]
        assert top_faller["diff"] < 0

    def test_movers_limit(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/scores/movers?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["risers"]) <= 1
        assert len(data["fallers"]) <= 1


class TestScoresParties:
    def test_parties_list(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/scores/parties")
        assert resp.status_code == 200
        data = resp.json()
        assert "自由民主党" in data
        assert "立憲民主党" in data
        assert "日本維新の会" in data

    def test_parties_filter_chamber(
        self, client: TestClient, rich_seed
    ):
        resp = client.get(
            "/api/v1/scores/parties?chamber=councillors"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "立憲民主党" in data
        # 衆院のみの自民党は含まれうるが、参院にもいるので含まれる
        # (member 4 は維新・参院)
        assert "日本維新の会" in data


# =====================================================================
# Bills API
# =====================================================================


class TestBillsList:
    def test_bills_list(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/bills")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_bills_filter_kind(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/bills?bill_kind=閣法")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "予算関連法案"

    def test_bills_filter_status(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/bills?status=審議中")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_bills_search(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/bills?search=環境")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "環境" in data["items"][0]["title"]

    def test_bills_pagination(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/bills?per_page=2&page=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["pages"] == 2


class TestBillDetail:
    def test_bill_detail(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/bills/2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "教育基本法改正案"
        assert len(data["sponsors"]) == 2
        # primary sponsor は田中太郎
        primary = [
            s for s in data["sponsors"]
            if s["sponsor_type"] == "primary"
        ]
        assert len(primary) == 1
        assert primary[0]["member_name"] == "田中太郎"

    def test_bill_detail_with_vote_results(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/bills/1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["vote_results"]) == 2
        chambers = {vr["chamber"] for vr in data["vote_results"]}
        assert "representatives" in chambers
        assert "councillors" in chambers

    def test_bill_not_found(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/bills/999")
        assert resp.status_code == 404


# =====================================================================
# Data Quality API
# =====================================================================


class TestDataQuality:
    def test_data_quality_summary(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/data-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_members"] == 5
        assert data["total_sessions"] == 2
        assert len(data["sessions"]) == 2
        # 会期215のデータ
        s215 = next(
            s for s in data["sessions"]
            if s["session_number"] == 215
        )
        assert s215["speech_count"] == 3
        assert s215["bill_count"] == 3
        assert s215["scored_member_count"] == 4

    def test_last_updated(self, client: TestClient, rich_seed):
        resp = client.get("/api/v1/data-quality/last-updated")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipelines" in data
        assert len(data["pipelines"]) >= 2
        # completed パイプラインがある
        completed = [
            p for p in data["pipelines"]
            if p["status"] == "completed"
        ]
        assert len(completed) >= 1
        assert data["last_updated"] is not None

    def test_last_updated_pipeline_details(
        self, client: TestClient, rich_seed
    ):
        resp = client.get("/api/v1/data-quality/last-updated")
        data = resp.json()
        names = {p["pipeline_name"] for p in data["pipelines"]}
        assert "members" in names
        assert "speeches" in names
        # scoring は failed のみなので status="never"
        scoring = next(
            (p for p in data["pipelines"]
             if p["pipeline_name"] == "scoring"),
            None,
        )
        if scoring:
            assert scoring["status"] == "never"


# =====================================================================
# Reviews API - PUT endpoint
# =====================================================================


class TestReviewUpdate:
    def _create_review(
        self, client: TestClient, member_id: int = 1
    ) -> dict:
        """ヘルパー: レビューを作成して返す。"""
        resp = client.post(
            f"/api/v1/members/{member_id}/reviews",
            json={
                "reviewer_id": "test-uuid-001",
                "display_name": "テストユーザー",
                "legislative_activity": 70,
                "voting_behavior": 60,
                "policy_influence": 50,
                "transparency": 40,
                "question_quality": 80,
                "comment": "良い議員です",
            },
        )
        assert resp.status_code == 200
        return resp.json()

    def test_update_review(self, client: TestClient, rich_seed):
        created = self._create_review(client)
        review_id = created["id"]
        resp = client.put(
            f"/api/v1/reviews/{review_id}",
            json={
                "reviewer_id": "test-uuid-001",
                "legislative_activity": 90,
                "comment": "やっぱりすごい",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["legislative_activity"] == 90
        assert data["comment"] == "やっぱりすごい"
        # 他のフィールドは変わらない
        assert data["voting_behavior"] == 60

    def test_update_review_recalculates_total(
        self, client: TestClient, rich_seed
    ):
        created = self._create_review(client)
        review_id = created["id"]
        resp = client.put(
            f"/api/v1/reviews/{review_id}",
            json={
                "reviewer_id": "test-uuid-001",
                "legislative_activity": 100,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        expected = (100 + 60 + 50 + 40 + 80) / 5
        assert abs(data["total"] - expected) < 0.1

    def test_update_review_wrong_reviewer(
        self, client: TestClient, rich_seed
    ):
        created = self._create_review(client)
        review_id = created["id"]
        resp = client.put(
            f"/api/v1/reviews/{review_id}",
            json={
                "reviewer_id": "wrong-uuid",
                "comment": "乗っ取り",
            },
        )
        assert resp.status_code == 403

    def test_update_review_not_found(
        self, client: TestClient, rich_seed
    ):
        resp = client.put(
            "/api/v1/reviews/9999",
            json={
                "reviewer_id": "test-uuid-001",
                "comment": "存在しない",
            },
        )
        assert resp.status_code == 404
