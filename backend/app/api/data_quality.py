from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bill import Bill
from app.models.member import Member
from app.models.pipeline import PipelineRun
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
    total_members = db.execute(select(func.count(Member.id))).scalar_one()

    sessions = (
        db.execute(select(DietSession).order_by(DietSession.session_number.desc())).scalars().all()
    )

    result: list[SessionDataQuality] = []
    for s in sessions:
        sid = s.id

        scored = db.execute(
            select(func.count(MemberScore.id)).where(MemberScore.session_id == sid)
        ).scalar_one()

        speech_count = db.execute(
            select(func.count(Speech.id)).where(Speech.session_id == sid)
        ).scalar_one()

        speakers = db.execute(
            select(func.count(func.distinct(Speech.member_id))).where(Speech.session_id == sid)
        ).scalar_one()

        bill_count = db.execute(
            select(func.count(Bill.id)).where(Bill.session_id == sid)
        ).scalar_one()

        vote_result_count = db.execute(
            select(func.count(VoteResult.id)).where(
                VoteResult.bill_id.in_(select(Bill.id).where(Bill.session_id == sid))
            )
        ).scalar_one()

        vote_record_count = db.execute(
            select(func.count(VoteRecord.id)).where(
                VoteRecord.vote_result_id.in_(
                    select(VoteResult.id).where(
                        VoteResult.bill_id.in_(select(Bill.id).where(Bill.session_id == sid))
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


class PipelineLastRun(BaseModel):
    pipeline_name: str
    status: str
    finished_at: str | None = None
    records_processed: int = 0


class LastUpdatedResponse(BaseModel):
    last_updated: str | None = None
    pipelines: list[PipelineLastRun]


@router.get("/last-updated", response_model=LastUpdatedResponse, summary="最終更新日時")
def get_last_updated(db: Session = Depends(get_db)):
    """各パイプラインの最終成功実行日時を返す。"""
    from sqlalchemy import distinct

    pipeline_names = db.execute(
        select(distinct(PipelineRun.pipeline_name))
    ).scalars().all()

    pipelines: list[PipelineLastRun] = []
    global_latest: str | None = None

    for name in sorted(pipeline_names):
        run = db.execute(
            select(PipelineRun)
            .where(PipelineRun.pipeline_name == name, PipelineRun.status == "completed")
            .order_by(PipelineRun.finished_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if run and run.finished_at:
            finished_str = run.finished_at.isoformat()
            pipelines.append(PipelineLastRun(
                pipeline_name=name,
                status=run.status,
                finished_at=finished_str,
                records_processed=run.records_processed,
            ))
            if global_latest is None or finished_str > global_latest:
                global_latest = finished_str
        else:
            pipelines.append(PipelineLastRun(
                pipeline_name=name,
                status="never",
            ))

    return LastUpdatedResponse(last_updated=global_latest, pipelines=pipelines)
