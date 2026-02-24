"""ランキングサービス

議員スコアのソート・フィルタリングを提供する。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.member import Member
from app.models.score import MemberScore
from app.models.session import DietSession


def get_ranking(
    db: Session,
    session_number: int | None = None,
    chamber: str | None = None,
    party: str | None = None,
    role_category: str | None = None,
    sort_by: str = "total",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """ランキングを取得する。"""
    query = select(MemberScore, Member).join(Member, MemberScore.member_id == Member.id)

    if session_number:
        session = db.execute(
            select(DietSession).where(DietSession.session_number == session_number)
        ).scalar_one_or_none()
        if session:
            query = query.where(MemberScore.session_id == session.id)
    else:
        latest = db.execute(
            select(DietSession).order_by(DietSession.session_number.desc()).limit(1)
        ).scalar_one_or_none()
        if latest:
            query = query.where(MemberScore.session_id == latest.id)

    if chamber:
        query = query.where(Member.chamber == chamber)
    if party:
        query = query.where(Member.party == party)
    if role_category:
        query = query.where(Member.role_category == role_category)

    sort_col = {
        "total": MemberScore.total,
        "legislative_activity": MemberScore.legislative_activity,
        "voting_behavior": MemberScore.voting_behavior,
        "policy_influence": MemberScore.policy_influence,
        "transparency": MemberScore.transparency,
    }.get(sort_by, MemberScore.total)

    query = query.order_by(sort_col.desc())
    results = db.execute(query.offset(offset).limit(limit)).all()

    return [
        {
            "rank": offset + i + 1,
            "member": member,
            "score": score,
        }
        for i, (score, member) in enumerate(results)
    ]
