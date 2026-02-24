"""国会会議録API クライアント

https://kokkai.ndl.go.jp/api/speech のREST APIからデータを取得する。
"""
import logging
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.member import Member
from app.models.pipeline import PipelineRun
from app.models.session import DietSession
from app.models.speech import Speech
from app.pipeline.member_master import normalize_name, find_or_create_member

logger = logging.getLogger(__name__)

RECORDS_PER_PAGE = 100
USER_AGENT = "GiinScore/0.1 (Data Pipeline)"


def fetch_speeches(db: Session, session_number: int, resume_from: int = 0) -> int:
    """指定会期の発言データを取得してDBに保存する。"""
    pipeline_run = PipelineRun(
        pipeline_name="kokkai_speeches",
        session_number=session_number,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(pipeline_run)
    db.commit()

    diet_session = db.query(DietSession).filter_by(session_number=session_number).first()
    if not diet_session:
        diet_session = DietSession(session_number=session_number, kind="通常")
        db.add(diet_session)
        db.commit()

    total_processed = 0
    start_record = resume_from + 1 if resume_from else 1

    try:
        with httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT}) as client:
            while True:
                params = {
                    "sessionFrom": session_number,
                    "sessionTo": session_number,
                    "recordPacking": "json",
                    "maximumRecords": RECORDS_PER_PAGE,
                    "startRecord": start_record,
                }

                time.sleep(settings.kokkai_api_rate_limit)

                try:
                    resp = client.get(f"{settings.kokkai_api_base_url}/speech", params=params)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.error(f"API request failed at record {start_record}: {e}")
                    break

                data = resp.json()
                number_of_records = data.get("numberOfRecords", 0)
                if number_of_records == 0:
                    break

                speech_records = data.get("speechRecord", [])
                if not speech_records:
                    break

                for record in speech_records:
                    try:
                        _process_speech_record(db, diet_session, record)
                        total_processed += 1
                    except Exception as e:
                        logger.warning(f"Failed to process speech record: {e}")

                if total_processed % 1000 == 0:
                    db.commit()
                    logger.info(f"Processed {total_processed} speeches")

                start_record += RECORDS_PER_PAGE
                if start_record > number_of_records:
                    break

        db.commit()
        pipeline_run.status = "completed"
        pipeline_run.records_processed = start_record - 1
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.info(f"Completed: {total_processed} speeches for session {session_number}")

    except Exception as e:
        pipeline_run.status = "failed"
        pipeline_run.error_message = str(e)
        pipeline_run.records_processed = start_record - 1
        pipeline_run.finished_at = datetime.utcnow()
        db.commit()
        logger.error(f"Pipeline failed: {e}")
        raise

    return total_processed


def _process_speech_record(db: Session, diet_session: DietSession, record: dict):
    speaker_name = record.get("speaker", "")
    if not speaker_name:
        return

    speaker_group = record.get("speakerGroup", "")
    speaker_role = record.get("speakerPosition", "")

    chamber = "representatives"
    meeting_name = record.get("nameOfMeeting", "")
    if "参議院" in record.get("nameOfHouse", ""):
        chamber = "councillors"

    member = find_or_create_member(
        db,
        name=normalize_name(speaker_name),
        chamber=chamber,
        party=speaker_group,
        role=speaker_role,
    )

    speech_text = record.get("speech", "")
    speech_date = None
    date_str = record.get("date", "")
    if date_str:
        try:
            speech_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    speech_url = record.get("speechURL", "")
    if speech_url:
        existing = db.query(Speech.id).filter_by(speech_url=speech_url).first()
        if existing:
            return

    speech = Speech(
        session_id=diet_session.id,
        member_id=member.id,
        meeting_name=meeting_name,
        speech_date=speech_date,
        speech_text=speech_text,
        speech_chars=len(speech_text),
        speech_url=speech_url,
    )
    db.add(speech)


def get_last_run(db: Session, session_number: int) -> int:
    """前回実行の最終レコード位置を取得する（完了・失敗いずれからも再開可能）。"""
    run = (
        db.query(PipelineRun)
        .filter_by(pipeline_name="kokkai_speeches", session_number=session_number)
        .filter(PipelineRun.status.in_(["completed", "failed"]))
        .order_by(PipelineRun.id.desc())
        .first()
    )
    if run and run.records_processed:
        return run.records_processed
    return 0
