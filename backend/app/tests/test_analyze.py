"""データ品質分析パイプライン (analyze.py) テスト"""

from datetime import UTC, date, datetime
from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.models.score import MemberScore
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.models.vote import VoteRecord, VoteResult
from app.models.written_question import WrittenQuestion
from app.pipeline.analyze import (
    _coverage_rate,
    _grade_distribution,
    analyze_data_quality,
)

# =====================================================================
# _coverage_rate
# =====================================================================


class TestCoverageRate:
    def test_high(self):
        assert "✅" in _coverage_rate(95, 100)

    def test_medium(self):
        assert "⚠️" in _coverage_rate(75, 100)

    def test_low(self):
        assert "❌" in _coverage_rate(50, 100)

    def test_zero_total(self):
        assert _coverage_rate(0, 0) == "N/A"

    def test_exact_90(self):
        assert "✅" in _coverage_rate(90, 100)

    def test_exact_70(self):
        assert "⚠️" in _coverage_rate(70, 100)


# =====================================================================
# _grade_distribution
# =====================================================================


class TestGradeDistribution:
    def test_basic(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        members = [
            Member(id=i, name=f"m{i}", chamber="representatives")
            for i in range(1, 6)
        ]
        db.add_all(members)
        db.flush()
        grades = ["A", "A", "B", "C", "F"]
        for i, g in enumerate(grades, 1):
            db.add(MemberScore(
                member_id=i, session_id=1, total=50, grade=g,
            ))
        db.commit()

        dist = _grade_distribution(db, 1)
        assert dist["A"] == 2
        assert dist["B"] == 1
        assert dist["C"] == 1
        assert dist["F"] == 1
        assert "D" not in dist

    def test_empty(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()
        dist = _grade_distribution(db, 1)
        assert dist == {}


# =====================================================================
# analyze_data_quality
# =====================================================================


class TestAnalyzeDataQuality:
    def _seed_full_data(self, db: Session):
        """分析テスト用のフルデータセット。"""
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()

        members = [
            Member(
                id=i, name=f"議員{i}",
                chamber="representatives",
                party="自由民主党",
            )
            for i in range(1, 11)
        ]
        db.add_all(members)
        db.flush()

        # スコア (8/10 → 80%)
        for i in range(1, 9):
            db.add(MemberScore(
                member_id=i, session_id=1,
                total=50 + i, grade="C",
            ))

        # 発言
        for i in range(1, 6):
            db.add(Speech(
                session_id=1, member_id=i,
                meeting_name="委員会",
                speech_date=date(2024, 1, i),
                speech_chars=100,
            ))

        # 法案
        b = Bill(
            id=1, session_id=1, bill_kind="閣法",
            title="テスト法案", status="成立",
        )
        db.add(b)
        db.flush()

        # 投票結果・記録
        vr = VoteResult(
            id=1, bill_id=1, chamber="representatives",
            ayes=100, nays=50, result="可決",
        )
        db.add(vr)
        db.flush()
        db.add(VoteRecord(
            vote_result_id=1, member_id=1, vote="aye",
        ))

        # 質問主意書
        db.add(WrittenQuestion(
            session_id=1, member_id=1,
            chamber="representatives",
            question_number=1,
            title="テスト質問",
        ))

        # 質問品質
        db.add(SpeechQualityScore(
            speech_id=1, member_id=1, session_id=1,
            policy_relevance=70, constructiveness=60,
            expertise=50, national_interest=80,
            overall_quality=65,
        ))

        # パイプライン実行記録
        db.add(PipelineRun(
            pipeline_name="speeches", session_number=215,
            status="completed",
            started_at=datetime(2024, 1, 1, tzinfo=UTC),
            finished_at=datetime(2024, 1, 1, 1, tzinfo=UTC),
            records_processed=100,
        ))

        db.commit()

    @patch("app.pipeline.analyze._send_webhook")
    def test_full_analysis(self, mock_webhook, db: Session):
        self._seed_full_data(db)
        result = analyze_data_quality(db, 215)
        assert result == 1
        mock_webhook.assert_called_once()
        embed = mock_webhook.call_args[0][0]
        assert "215" in embed["description"]
        assert "議員数" in embed["description"]

    @patch("app.pipeline.analyze._send_webhook")
    def test_analysis_reports_gaps(
        self, mock_webhook, db: Session
    ):
        """発言0件などのギャップを検出する。"""
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        for i in range(1, 11):
            db.add(Member(
                id=i, name=f"議員{i}",
                chamber="representatives",
            ))
        db.commit()

        result = analyze_data_quality(db, 215)
        assert result == 1
        embed = mock_webhook.call_args[0][0]
        # ギャップが検出される
        assert "発言データが0件" in embed["description"]
        assert "法案データが0件" in embed["description"]

    @patch("app.pipeline.analyze._send_webhook")
    def test_session_not_found(
        self, mock_webhook, db: Session
    ):
        result = analyze_data_quality(db, 999)
        assert result == 0
        mock_webhook.assert_not_called()

    @patch("app.pipeline.analyze._send_webhook")
    def test_grade_distribution_in_report(
        self, mock_webhook, db: Session
    ):
        self._seed_full_data(db)
        analyze_data_quality(db, 215)
        embed = mock_webhook.call_args[0][0]
        assert "グレード分布" in embed["description"]
        assert "C:" in embed["description"]
