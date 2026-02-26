from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.database import get_db
from app.models.member import Member
from app.models.score import MemberScore
from app.models.speech import Speech
from app.models.vote import VoteRecord, VoteResult
from app.schemas.common import PaginatedResponse
from app.schemas.member import MemberDetail, MemberWithScore, ScoreDetail, ScoreSummary
from app.schemas.speech import SpeechResponse
from app.schemas.vote import VoteRecordResponse

router = APIRouter(prefix="/members", tags=["members"])

# スコアソート可能なフィールド
SCORE_SORT_FIELDS = {
    "total": MemberScore.total,
    "legislative_activity": MemberScore.legislative_activity,
    "voting_behavior": MemberScore.voting_behavior,
    "policy_influence": MemberScore.policy_influence,
    "transparency": MemberScore.transparency,
}


@router.get("", response_model=PaginatedResponse[MemberWithScore])
def list_members(
    chamber: Literal["representatives", "councillors"] | None = None,
    party: str | None = None,
    role_category: str | None = None,
    search: str | None = None,
    district: str | None = None,
    sort_by: Literal[
        "name",
        "total",
        "legislative_activity",
        "voting_behavior",
        "policy_influence",
        "transparency",
    ] = "name",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    # 最新スコアのサブクエリ
    latest_score_sq = (
        select(
            MemberScore.member_id,
            func.max(MemberScore.session_id).label("max_session_id"),
        )
        .group_by(MemberScore.member_id)
        .subquery()
    )

    LatestScore = aliased(MemberScore)

    # メインクエリ: Member + 最新スコアをJOIN
    query = (
        select(Member, LatestScore)
        .outerjoin(
            latest_score_sq,
            Member.id == latest_score_sq.c.member_id,
        )
        .outerjoin(
            LatestScore,
            (LatestScore.member_id == latest_score_sq.c.member_id)
            & (LatestScore.session_id == latest_score_sq.c.max_session_id),
        )
    )

    count_query = select(func.count(Member.id))

    if chamber:
        query = query.where(Member.chamber == chamber)
        count_query = count_query.where(Member.chamber == chamber)
    if party:
        query = query.where(Member.party == party)
        count_query = count_query.where(Member.party == party)
    if role_category:
        query = query.where(Member.role_category == role_category)
        count_query = count_query.where(Member.role_category == role_category)
    if district:
        query = query.where(Member.district.ilike(f"%{district}%"))
        count_query = count_query.where(Member.district.ilike(f"%{district}%"))
    if search:
        query = query.where(Member.name.ilike(f"%{search}%"))
        count_query = count_query.where(Member.name.ilike(f"%{search}%"))

    total = db.execute(count_query).scalar_one()

    # ソート
    if sort_by in SCORE_SORT_FIELDS:
        score_col = getattr(LatestScore, sort_by)
        query = query.order_by(score_col.desc().nullslast(), Member.name)
    else:
        query = query.order_by(Member.name)

    offset = (page - 1) * per_page
    rows = db.execute(query.offset(offset).limit(per_page)).all()

    items = []
    for member, score in rows:
        score_summary = None
        if score:
            score_summary = ScoreSummary(
                total=score.total,
                grade=score.grade,
                legislative_activity=score.legislative_activity,
                voting_behavior=score.voting_behavior,
                policy_influence=score.policy_influence,
                transparency=score.transparency,
            )
        items.append(
            MemberWithScore(
                id=member.id,
                name=member.name,
                name_reading=member.name_reading,
                chamber=member.chamber,
                party=member.party,
                faction=member.faction,
                district=member.district,
                role_category=member.role_category,
                latest_score=score_summary,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page else 0,
    )


@router.get("/districts", response_model=list[str])
def get_districts(
    chamber: Literal["representatives", "councillors"] | None = None,
    db: Session = Depends(get_db),
):
    """データベースに存在する選挙区名一覧を返す。"""
    query = (
        select(Member.district)
        .where(Member.district.isnot(None))
        .distinct()
        .order_by(Member.district)
    )
    if chamber:
        query = query.where(Member.chamber == chamber)
    districts = db.execute(query).scalars().all()
    return [d for d in districts if d]


@router.get("/{member_id}", response_model=MemberDetail)
def get_member(member_id: int, db: Session = Depends(get_db)):
    member = db.execute(
        select(Member).where(Member.id == member_id).options(selectinload(Member.scores))
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    scores = []
    for s in member.scores:
        session_num = None
        if s.session:
            session_num = s.session.session_number
        scores.append(
            ScoreDetail(
                id=s.id,
                session_id=s.session_id,
                session_number=session_num,
                legislative_activity_raw=s.legislative_activity_raw,
                voting_behavior_raw=s.voting_behavior_raw,
                policy_influence_raw=s.policy_influence_raw,
                transparency_raw=s.transparency_raw,
                legislative_activity=s.legislative_activity,
                voting_behavior=s.voting_behavior,
                policy_influence=s.policy_influence,
                transparency=s.transparency,
                total=s.total,
                grade=s.grade,
                breakdown=s.breakdown,
            )
        )

    return MemberDetail(
        id=member.id,
        name=member.name,
        name_reading=member.name_reading,
        chamber=member.chamber,
        party=member.party,
        faction=member.faction,
        district=member.district,
        role_category=member.role_category,
        scores=scores,
    )


@router.get("/{member_id}/scores", response_model=list[ScoreDetail])
def get_member_scores(member_id: int, db: Session = Depends(get_db)):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    scores = (
        db.execute(
            select(MemberScore)
            .where(MemberScore.member_id == member_id)
            .options(selectinload(MemberScore.session))
            .order_by(MemberScore.session_id.desc())
        )
        .scalars()
        .all()
    )
    result = []
    for s in scores:
        session_num = None
        if s.session:
            session_num = s.session.session_number
        result.append(
            ScoreDetail(
                id=s.id,
                session_id=s.session_id,
                session_number=session_num,
                legislative_activity_raw=s.legislative_activity_raw,
                voting_behavior_raw=s.voting_behavior_raw,
                policy_influence_raw=s.policy_influence_raw,
                transparency_raw=s.transparency_raw,
                legislative_activity=s.legislative_activity,
                voting_behavior=s.voting_behavior,
                policy_influence=s.policy_influence,
                transparency=s.transparency,
                total=s.total,
                grade=s.grade,
                breakdown=s.breakdown,
            )
        )
    return result


@router.get("/{member_id}/speeches", response_model=PaginatedResponse[SpeechResponse])
def get_member_speeches(
    member_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    total = db.execute(
        select(func.count(Speech.id)).where(Speech.member_id == member_id)
    ).scalar_one()
    offset = (page - 1) * per_page
    speeches = (
        db.execute(
            select(Speech)
            .where(Speech.member_id == member_id)
            .order_by(Speech.speech_date.desc().nullslast())
            .offset(offset)
            .limit(per_page)
        )
        .scalars()
        .all()
    )

    items = [
        SpeechResponse(
            id=s.id,
            meeting_name=s.meeting_name,
            speech_date=str(s.speech_date) if s.speech_date else None,
            speech_chars=s.speech_chars,
            speech_url=s.speech_url,
        )
        for s in speeches
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page else 0,
    )


@router.get("/{member_id}/votes", response_model=PaginatedResponse[VoteRecordResponse])
def get_member_votes(
    member_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    total = db.execute(
        select(func.count(VoteRecord.id)).where(VoteRecord.member_id == member_id)
    ).scalar_one()
    offset = (page - 1) * per_page
    records = (
        db.execute(
            select(VoteRecord)
            .where(VoteRecord.member_id == member_id)
            .options(selectinload(VoteRecord.vote_result).selectinload(VoteResult.bill))
            .offset(offset)
            .limit(per_page)
        )
        .scalars()
        .all()
    )

    items = []
    for r in records:
        bill_title = None
        if r.vote_result and r.vote_result.bill:
            bill_title = r.vote_result.bill.title
        items.append(
            VoteRecordResponse(
                id=r.id,
                vote_result_id=r.vote_result_id,
                member_id=r.member_id,
                member_name=member.name,
                vote=r.vote,
                bill_title=bill_title,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page else 0,
    )
