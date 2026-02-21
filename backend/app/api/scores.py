import statistics

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.member import Member
from app.models.score import MemberScore
from app.models.session import DietSession
from app.schemas.member import MemberResponse
from app.schemas.score import (
    RankingEntry,
    RankingResponse,
    ScoreDistribution,
    ScoreResponse,
    StatsResponse,
)

router = APIRouter(prefix="/scores", tags=["scores"])


def _resolve_session_id(db: Session, session_number: int | None) -> int | None:
    """指定会期またはスコアが存在する最新会期のIDを返す。"""
    if session_number:
        session = db.execute(
            select(DietSession).where(DietSession.session_number == session_number)
        ).scalar_one_or_none()
        return session.id if session else None

    # スコアが存在する最新の会期を取得
    from sqlalchemy import func as sa_func
    latest_scored = db.execute(
        select(DietSession.id)
        .where(
            DietSession.id.in_(
                select(MemberScore.session_id).distinct()
            )
        )
        .order_by(DietSession.session_number.desc())
        .limit(1)
    ).scalar_one_or_none()
    return latest_scored


@router.get("/ranking", response_model=RankingResponse)
def get_ranking(
    chamber: str | None = None,
    party: str | None = None,
    role_category: str | None = None,
    session_number: int | None = None,
    sort_by: str = "total",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(MemberScore).options(selectinload(MemberScore.member))

    session_id = _resolve_session_id(db, session_number)
    if session_id:
        query = query.where(MemberScore.session_id == session_id)

    if chamber:
        query = query.join(Member).where(Member.chamber == chamber)
    elif party or role_category:
        query = query.join(Member)

    if party:
        query = query.where(Member.party == party)
    if role_category:
        query = query.where(Member.role_category == role_category)

    sort_column = {
        "total": MemberScore.total,
        "legislative_activity": MemberScore.legislative_activity,
        "voting_behavior": MemberScore.voting_behavior,
        "policy_influence": MemberScore.policy_influence,
        "transparency": MemberScore.transparency,
    }.get(sort_by, MemberScore.total)

    all_scores = db.execute(query.order_by(sort_column.desc())).scalars().all()
    total = len(all_scores)
    paged = all_scores[offset : offset + limit]

    items = []
    for i, s in enumerate(paged):
        items.append(
            RankingEntry(
                rank=offset + i + 1,
                member=MemberResponse.model_validate(s.member),
                score=ScoreResponse.model_validate(s),
            )
        )

    return RankingResponse(
        items=items,
        total=total,
        chamber=chamber,
        party=party,
        session_number=session_number,
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    chamber: str | None = None,
    session_number: int | None = None,
    db: Session = Depends(get_db),
):
    query = select(MemberScore)

    session_id = _resolve_session_id(db, session_number)
    if session_id:
        query = query.where(MemberScore.session_id == session_id)

    if chamber:
        query = query.join(Member).where(Member.chamber == chamber)

    scores = db.execute(query).scalars().all()
    totals = [s.total for s in scores]

    if not totals:
        return StatsResponse(
            total_members=0,
            average_score=0.0,
            median_score=0.0,
            max_score=0.0,
            min_score=0.0,
            distribution=[],
            chamber=chamber,
            session_number=session_number,
        )

    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for s in scores:
        grades[s.grade] = grades.get(s.grade, 0) + 1

    n = len(totals)
    distribution = [
        ScoreDistribution(grade=g, count=c, percentage=round(c / n * 100, 1))
        for g, c in grades.items()
    ]

    return StatsResponse(
        total_members=n,
        average_score=round(statistics.mean(totals), 1),
        median_score=round(statistics.median(totals), 1),
        max_score=round(max(totals), 1),
        min_score=round(min(totals), 1),
        distribution=distribution,
        chamber=chamber,
        session_number=session_number,
    )
