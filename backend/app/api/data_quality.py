from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bill import Bill
from app.models.member import Member
from app.models.score import MemberScore
from app.models.session import DietSession
from app.models.speech import Speech
from app.models.vote import VoteRecord, VoteResult

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


class SessionDataQuality(BaseModel):
    session_number: int
    session_kind: str
    member_count: int
    scored_member_count: int
    speech_count: int
    speakers_count: int
    bill_count: int
    vote_result_count: int
    vote_record_count: int


class DataQualityResponse(BaseModel):
    total_members: int
    total_sessions: int
    sessions: list[SessionDataQuality]


@router.get("", response_model=DataQualityResponse, summary="データ品質概要取得")
def get_data_quality(db: Session = Depends(get_db)):
    """会期ごとのデータ充足状況を返す。"""
    total_members = db.execute(
        select(func.count(Member.id))
    ).scalar_one()

    sessions = (
        db.execute(
            select(DietSession).order_by(DietSession.session_number.desc())
        )
        .scalars()
        .all()
    )

    result: list[SessionDataQuality] = []
    for s in sessions:
        sid = s.id

        scored = db.execute(
            select(func.count(MemberScore.id)).where(
                MemberScore.session_id == sid
            )
        ).scalar_one()

        speech_count = db.execute(
            select(func.count(Speech.id)).where(Speech.session_id == sid)
        ).scalar_one()

        speakers = db.execute(
            select(func.count(func.distinct(Speech.member_id))).where(
                Speech.session_id == sid
            )
        ).scalar_one()

        bill_count = db.execute(
            select(func.count(Bill.id)).where(Bill.session_id == sid)
        ).scalar_one()

        vote_result_count = db.execute(
            select(func.count(VoteResult.id)).where(
                VoteResult.bill_id.in_(
                    select(Bill.id).where(Bill.session_id == sid)
                )
            )
        ).scalar_one()

        vote_record_count = db.execute(
            select(func.count(VoteRecord.id)).where(
                VoteRecord.vote_result_id.in_(
                    select(VoteResult.id).where(
                        VoteResult.bill_id.in_(
                            select(Bill.id).where(
                                Bill.session_id == sid
                            )
                        )
                    )
                )
            )
        ).scalar_one()

        result.append(
            SessionDataQuality(
                session_number=s.session_number,
                session_kind=s.kind,
                member_count=total_members,
                scored_member_count=scored,
                speech_count=speech_count,
                speakers_count=speakers,
                bill_count=bill_count,
                vote_result_count=vote_result_count,
                vote_record_count=vote_record_count,
            )
        )

    return DataQualityResponse(
        total_members=total_members,
        total_sessions=len(sessions),
        sessions=result,
    )
