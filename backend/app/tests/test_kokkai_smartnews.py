"""国会API・SmartNewsローダーのテスト可能部分

外部HTTP呼び出しは最小限のモック、パース・DB保存ロジックは実物で実行。
"""

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.models.session import DietSession
from app.models.speech import Speech
from app.pipeline.kokkai_api import (
    EXCLUDED_SPEAKERS,
    _process_speech_record,
    get_last_run,
)
from app.pipeline.smartnews_loader import (
    _get_field,
    _process_bill_row,
)

# =====================================================================
# kokkai_api.py
# =====================================================================


class TestProcessSpeechRecord:
    def test_basic(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        record = {
            "speaker": "田中太郎",
            "speakerGroup": "自由民主党",
            "speakerPosition": "",
            "nameOfHouse": "衆議院",
            "nameOfMeeting": "予算委員会",
            "speech": "あ" * 100,
            "date": "2024-02-15",
            "speechURL": "https://example.com/speech/1",
        }
        _process_speech_record(db, s, record)
        db.commit()

        speeches = db.query(Speech).all()
        assert len(speeches) == 1
        assert speeches[0].member.name == "田中太郎"
        assert speeches[0].speech_chars == 100

    def test_sangiin_chamber(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        record = {
            "speaker": "鈴木花子",
            "nameOfHouse": "参議院",
            "nameOfMeeting": "予算委員会",
            "speech": "テスト",
            "date": "2024-02-15",
        }
        _process_speech_record(db, s, record)
        db.commit()

        member = db.query(Member).first()
        assert member.chamber == "councillors"

    def test_excluded_speaker_skipped(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        for excluded in EXCLUDED_SPEAKERS:
            record = {
                "speaker": excluded,
                "nameOfHouse": "衆議院",
                "speech": "テスト",
            }
            _process_speech_record(db, s, record)

        db.commit()
        assert db.query(Speech).count() == 0

    def test_empty_speaker_skipped(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        record = {
            "speaker": "",
            "nameOfHouse": "衆議院",
            "speech": "テスト",
        }
        _process_speech_record(db, s, record)
        db.commit()
        assert db.query(Speech).count() == 0

    def test_duplicate_url_skipped(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        record = {
            "speaker": "田中太郎",
            "nameOfHouse": "衆議院",
            "speech": "テスト1",
            "speechURL": "https://example.com/dup",
        }
        _process_speech_record(db, s, record)
        db.commit()

        # 同じURL → スキップ
        record2 = {
            "speaker": "田中太郎",
            "nameOfHouse": "衆議院",
            "speech": "テスト2",
            "speechURL": "https://example.com/dup",
        }
        _process_speech_record(db, s, record2)
        db.commit()

        assert db.query(Speech).count() == 1

    def test_invalid_date(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        record = {
            "speaker": "田中太郎",
            "nameOfHouse": "衆議院",
            "speech": "テスト",
            "date": "invalid-date",
        }
        _process_speech_record(db, s, record)
        db.commit()

        speech = db.query(Speech).first()
        assert speech is not None
        assert speech.speech_date is None


class TestGetLastRun:
    def test_no_runs(self, db: Session):
        assert get_last_run(db, 215) == 0

    def test_completed_run(self, db: Session):
        db.add(
            PipelineRun(
                pipeline_name="kokkai_speeches",
                session_number=215,
                status="completed",
                records_processed=500,
                started_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )
        db.commit()
        assert get_last_run(db, 215) == 500

    def test_failed_run(self, db: Session):
        db.add(
            PipelineRun(
                pipeline_name="kokkai_speeches",
                session_number=215,
                status="failed",
                records_processed=300,
                started_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )
        db.commit()
        assert get_last_run(db, 215) == 300

    def test_running_ignored(self, db: Session):
        db.add(
            PipelineRun(
                pipeline_name="kokkai_speeches",
                session_number=215,
                status="running",
                records_processed=100,
                started_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )
        db.commit()
        assert get_last_run(db, 215) == 0

    def test_latest_used(self, db: Session):
        db.add(
            PipelineRun(
                id=1,
                pipeline_name="kokkai_speeches",
                session_number=215,
                status="completed",
                records_processed=100,
                started_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )
        db.add(
            PipelineRun(
                id=2,
                pipeline_name="kokkai_speeches",
                session_number=215,
                status="completed",
                records_processed=500,
                started_at=datetime(2024, 1, 2, tzinfo=UTC),
            )
        )
        db.commit()
        assert get_last_run(db, 215) == 500


# =====================================================================
# smartnews_loader.py
# =====================================================================


class TestGetField:
    def test_first_candidate(self):
        row = pd.Series({"session": "215", "title": "法案A"})
        assert _get_field(row, ["session"]) == "215"

    def test_second_candidate(self):
        row = pd.Series({"国会回次": "215"})
        assert _get_field(row, ["session", "国会回次"]) == "215"

    def test_missing(self):
        row = pd.Series({"other": "val"})
        assert _get_field(row, ["session", "国会回次"]) is None

    def test_nan_skipped(self):
        row = pd.Series({"session": float("nan")})
        assert _get_field(row, ["session"]) is None

    def test_strips_whitespace(self):
        row = pd.Series({"title": "  法案A  "})
        assert _get_field(row, ["title"]) == "法案A"


class TestProcessBillRow:
    def test_basic(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        row = pd.Series(
            {
                "session": "215",
                "bill_kind": "閣法",
                "bill_number": "1",
                "title": "テスト法案",
                "status": "成立",
                "result": "可決",
                "proposer_type": "cabinet",
                "url": "https://example.com",
            }
        )
        result = _process_bill_row(db, row)
        db.commit()
        assert result is True

        bill = db.query(Bill).first()
        assert bill.title == "テスト法案"
        assert bill.bill_kind == "閣法"
        assert bill.status == "成立"

    def test_creates_session_if_missing(self, db: Session):
        row = pd.Series(
            {
                "session": "999",
                "title": "新会期法案",
            }
        )
        result = _process_bill_row(db, row)
        db.commit()
        assert result is True

        s = db.query(DietSession).filter_by(session_number=999).first()
        assert s is not None

    def test_duplicate_skipped(self, db: Session):
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.flush()
        db.add(
            Bill(
                session_id=1,
                bill_kind="閣法",
                title="既存法案",
            )
        )
        db.commit()

        row = pd.Series(
            {
                "session": "215",
                "bill_kind": "閣法",
                "title": "既存法案",
            }
        )
        assert _process_bill_row(db, row) is False

    def test_missing_title(self, db: Session):
        row = pd.Series({"session": "215"})
        assert _process_bill_row(db, row) is False

    def test_missing_session(self, db: Session):
        row = pd.Series({"title": "法案A"})
        assert _process_bill_row(db, row) is False

    def test_japanese_column_names(self, db: Session):
        """日本語カラム名のCSVもパースできる。"""
        row = pd.Series(
            {
                "国会回次": "215",
                "議案種類": "衆法",
                "議案番号": "5",
                "議案名": "教育法案",
                "審議状況": "審議中",
            }
        )
        s = DietSession(id=1, session_number=215, kind="通常")
        db.add(s)
        db.commit()

        result = _process_bill_row(db, row)
        db.commit()
        assert result is True

        bill = db.query(Bill).first()
        assert bill.title == "教育法案"
        assert bill.bill_kind == "衆法"
