from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.bill import Bill, BillSponsor
from app.models.session import DietSession
from app.schemas.bill import BillDetail, BillResponse, SponsorInfo, VoteResultSummary
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/bills", tags=["bills"])


@router.get("", response_model=PaginatedResponse[BillResponse], summary="法案一覧取得")
def list_bills(
    session_number: int | None = None,
    bill_kind: str | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """法案一覧を返す。会期・種別・状態・タイトル検索でフィルタリング可能。"""
    query = select(Bill)
    count_query = select(func.count(Bill.id))

    if session_number:
        session = db.execute(
            select(DietSession).where(DietSession.session_number == session_number)
        ).scalar_one_or_none()
        if session:
            query = query.where(Bill.session_id == session.id)
            count_query = count_query.where(Bill.session_id == session.id)
    if bill_kind:
        query = query.where(Bill.bill_kind == bill_kind)
        count_query = count_query.where(Bill.bill_kind == bill_kind)
    if status:
        query = query.where(Bill.status == status)
        count_query = count_query.where(Bill.status == status)
    if search:
        query = query.where(Bill.title.ilike(f"%{search}%"))
        count_query = count_query.where(Bill.title.ilike(f"%{search}%"))

    total = db.execute(count_query).scalar_one()
    offset = (page - 1) * per_page
    bills = (
        db.execute(query.order_by(Bill.id.desc()).offset(offset).limit(per_page)).scalars().all()
    )

    return PaginatedResponse(
        items=[BillResponse.model_validate(b) for b in bills],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if per_page else 0,
    )


@router.get("/{bill_id}", response_model=BillDetail, summary="法案詳細取得")
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    """指定IDの法案の詳細（提出者・投票結果含む）を返す。"""
    bill = db.execute(
        select(Bill)
        .where(Bill.id == bill_id)
        .options(
            selectinload(Bill.sponsors).selectinload(BillSponsor.member),
            selectinload(Bill.vote_results),
        )
    ).scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    sponsors = [
        SponsorInfo(
            member_id=s.member_id,
            member_name=s.member.name if s.member else "Unknown",
            sponsor_type=s.sponsor_type,
        )
        for s in bill.sponsors
    ]
    vote_results = [
        VoteResultSummary(
            id=vr.id,
            chamber=vr.chamber,
            ayes=vr.ayes,
            nays=vr.nays,
            result=vr.result,
        )
        for vr in bill.vote_results
    ]

    return BillDetail(
        id=bill.id,
        session_id=bill.session_id,
        bill_kind=bill.bill_kind,
        bill_number=bill.bill_number,
        title=bill.title,
        status=bill.status,
        result=bill.result,
        proposer_type=bill.proposer_type,
        url=bill.url,
        sponsors=sponsors,
        vote_results=vote_results,
    )
