from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import DietSession
from app.schemas.session import SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse], summary="会期一覧取得")
def list_sessions(db: Session = Depends(get_db)):
    """登録されている国会会期一覧を降順で返す。"""
    sessions = (
        db.execute(select(DietSession).order_by(DietSession.session_number.desc())).scalars().all()
    )
    return [SessionResponse.model_validate(s) for s in sessions]
