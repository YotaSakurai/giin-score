from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.database import get_db
from app.models.member import Member
from app.models.score import MemberScore
from app.models.speech import Speech
from app.models.speech_quality import SpeechQualityScore
from app.models.vote import VoteRecord, VoteResult
from app.schemas.common import PaginatedResponse
from app.schemas.member import MemberDetail, MemberWithScore, ScoreDetail, ScoreSummary
from app.schemas.speech import SpeechResponse
from app.schemas.speech_quality import SpeechQualityResponse
from app.schemas.vote import DissentDetail, VotePatternResponse, VoteRecordResponse

router = APIRouter(prefix="/members", tags=["members"])

# スコアソート可能なフィールド
SCORE_SORT_FIELDS = {
    "total": MemberScore.total,
    "legislative_activity": MemberScore.legislative_activity,
    "voting_behavior": MemberScore.voting_behavior,
    "policy_influence": MemberScore.policy_influence,
    "transparency": MemberScore.transparency,
    "question_quality": MemberScore.question_quality,
}


@router.get("", response_model=PaginatedResponse[MemberWithScore], summary="議員一覧取得")
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
        "question_quality",
    ] = "name",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """議員一覧を最新スコア付きで返す。

    院・政党・選挙区・名前でフィルタリングし、スコア各軸でソート可能。
    """
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
                question_quality=score.question_quality,
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


@router.get("/districts", response_model=list[str], summary="選挙区一覧取得")
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


@router.get("/{member_id}", response_model=MemberDetail, summary="議員詳細取得")
def get_member(member_id: int, db: Session = Depends(get_db)):
    """指定IDの議員詳細（プロフィール・全会期スコア）を返す。"""
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
                question_quality_raw=s.question_quality_raw,
                legislative_activity=s.legislative_activity,
                voting_behavior=s.voting_behavior,
                policy_influence=s.policy_influence,
                transparency=s.transparency,
                question_quality=s.question_quality,
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


@router.get("/{member_id}/scores", response_model=list[ScoreDetail], summary="議員スコア履歴取得")
def get_member_scores(member_id: int, db: Session = Depends(get_db)):
    """指定議員の全会期スコア履歴を降順で返す。"""
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


@router.get(
    "/{member_id}/speeches",
    response_model=PaginatedResponse[SpeechResponse],
    summary="議員発言一覧取得",
)
def get_member_speeches(
    member_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """指定議員の国会発言一覧をページングで返す。"""
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


@router.get(
    "/{member_id}/votes",
    response_model=PaginatedResponse[VoteRecordResponse],
    summary="議員投票記録取得",
)
def get_member_votes(
    member_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """指定議員の投票記録をページングで返す。"""
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


@router.get(
    "/{member_id}/speech-quality",
    response_model=PaginatedResponse[SpeechQualityResponse],
    summary="議員の発言品質スコア一覧",
)
def get_member_speech_quality(
    member_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """指定議員の発言品質スコア一覧をページングで返す。"""
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    total = db.execute(
        select(func.count(SpeechQualityScore.id)).where(SpeechQualityScore.member_id == member_id)
    ).scalar_one()
    offset = (page - 1) * per_page

    quality_scores = (
        db.execute(
            select(SpeechQualityScore)
            .where(SpeechQualityScore.member_id == member_id)
            .options(selectinload(SpeechQualityScore.speech))
            .order_by(SpeechQualityScore.overall_quality.desc())
            .offset(offset)
            .limit(per_page)
        )
        .scalars()
        .all()
    )

    items = []
    for qs in quality_scores:
        speech = qs.speech
        items.append(
            SpeechQualityResponse(
                id=qs.id,
                speech_id=qs.speech_id,
                meeting_name=speech.meeting_name if speech else None,
                speech_date=str(speech.speech_date) if speech and speech.speech_date else None,
                speech_chars=speech.speech_chars if speech else 0,
                policy_relevance=qs.policy_relevance,
                constructiveness=qs.constructiveness,
                expertise=qs.expertise,
                national_interest=qs.national_interest,
                overall_quality=qs.overall_quality,
                analysis_summary=qs.analysis_summary,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page else 0,
    )


@router.get(
    "/{member_id}/vote-pattern",
    response_model=VotePatternResponse,
    summary="投票パターン分析",
)
def get_vote_pattern(member_id: int, db: Session = Depends(get_db)):
    """議員の投票パターン分析（造反率）を返す。"""
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # この議員の全投票記録を取得
    records = (
        db.execute(
            select(VoteRecord)
            .where(VoteRecord.member_id == member_id)
            .options(
                selectinload(VoteRecord.vote_result).selectinload(VoteResult.records),
                selectinload(VoteRecord.vote_result).selectinload(VoteResult.bill),
            )
        )
        .scalars()
        .all()
    )

    if not records:
        return VotePatternResponse(
            member_id=member_id,
            total_votes=0,
            party_majority_votes=0,
            dissent_votes=0,
            dissent_rate=0.0,
            absent_count=0,
            participation_rate=0.0,
            dissent_details=[],
        )

    # 同じ政党の議員のIDを取得
    party_member_ids: set[int] = set()
    if member.party:
        party_members = (
            db.execute(
                select(Member.id).where(
                    Member.party == member.party, Member.chamber == member.chamber
                )
            )
            .scalars()
            .all()
        )
        party_member_ids = set(party_members)

    total_votes = 0
    absent_count = 0
    dissent_votes = 0
    party_majority_votes = 0
    dissent_details: list[DissentDetail] = []

    for record in records:
        if record.vote == "absent":
            absent_count += 1
            continue

        total_votes += 1

        if not party_member_ids or not record.vote_result:
            continue

        # 同じ投票案件での同党議員の投票を集計
        party_votes = {"aye": 0, "nay": 0}
        for other_record in record.vote_result.records:
            if other_record.member_id in party_member_ids and other_record.member_id != member_id:
                if other_record.vote in party_votes:
                    party_votes[other_record.vote] += 1

        # 党の多数派を決定
        if party_votes["aye"] + party_votes["nay"] == 0:
            continue

        party_majority = "aye" if party_votes["aye"] >= party_votes["nay"] else "nay"
        party_majority_votes += 1

        if record.vote in ("aye", "nay") and record.vote != party_majority:
            dissent_votes += 1
            bill_title = None
            if record.vote_result.bill:
                bill_title = record.vote_result.bill.title
            dissent_details.append(
                DissentDetail(
                    bill_title=bill_title,
                    member_vote=record.vote,
                    party_majority_vote=party_majority,
                )
            )

    all_opportunities = total_votes + absent_count
    dissent_rate = (
        round(dissent_votes / party_majority_votes * 100, 1) if party_majority_votes > 0 else 0.0
    )
    participation_rate = (
        round(total_votes / all_opportunities * 100, 1) if all_opportunities > 0 else 0.0
    )

    return VotePatternResponse(
        member_id=member_id,
        total_votes=total_votes,
        party_majority_votes=party_majority_votes,
        dissent_votes=dissent_votes,
        dissent_rate=dissent_rate,
        absent_count=absent_count,
        participation_rate=participation_rate,
        dissent_details=dissent_details[:10],
    )
