"""居眠り検出 API

検出結果の閲覧・レビュー（承認/却下）エンドポイント。
管理者認証が必要なエンドポイントは Authorization: Bearer <ADMIN_TOKEN> ヘッダーを要求する。
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.member import Member
from app.models.session import DietSession
from app.models.sleeping_detection import SleepingDetection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sleeping", tags=["sleeping"])
limiter = Limiter(key_func=get_remote_address)


def _require_admin(authorization: str = Header(None)):
    """Admin認証ガード。ADMIN_TOKEN が未設定の場合は全拒否。"""
    if not settings.admin_token:
        raise HTTPException(status_code=403, detail="Admin access not configured")
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


class SleepingDetectionResponse(BaseModel):
    id: int
    member_id: int | None
    member_name: str | None = None
    session_id: int
    session_number: int | None = None
    video_url: str
    video_date: str | None
    meeting_name: str | None
    start_time_sec: float
    end_time_sec: float
    duration_sec: float
    detection_type: str
    confidence: float
    head_angle_avg: float | None
    screenshot_path: str | None
    clip_path: str | None
    identified_by: str | None
    identification_confidence: float | None
    seat_position: str | None
    review_status: str
    reviewed_at: str | None
    review_note: str | None
    detected_at: str

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    status: str  # approved / rejected
    note: str | None = None
    member_id: int | None = None  # レビュー時に議員を手動紐付け可能


class SleepingStatsResponse(BaseModel):
    total_detections: int
    pending: int
    approved: int
    rejected: int
    members_with_incidents: int


class AdminAuthRequest(BaseModel):
    token: str


class AdminAuthResponse(BaseModel):
    valid: bool


def _build_response(det: SleepingDetection, db: Session) -> SleepingDetectionResponse:
    """SleepingDetection → SleepingDetectionResponse 変換ヘルパー。"""
    member_name = None
    if det.member_id:
        member = db.get(Member, det.member_id)
        if member:
            member_name = member.name

    session_number = None
    session = db.get(DietSession, det.session_id)
    if session:
        session_number = session.session_number

    return SleepingDetectionResponse(
        id=det.id,
        member_id=det.member_id,
        member_name=member_name,
        session_id=det.session_id,
        session_number=session_number,
        video_url=det.video_url,
        video_date=det.video_date.isoformat() if det.video_date else None,
        meeting_name=det.meeting_name,
        start_time_sec=det.start_time_sec,
        end_time_sec=det.end_time_sec,
        duration_sec=det.duration_sec,
        detection_type=det.detection_type,
        confidence=det.confidence,
        head_angle_avg=det.head_angle_avg,
        screenshot_path=det.screenshot_path,
        clip_path=det.clip_path,
        identified_by=det.identified_by,
        identification_confidence=det.identification_confidence,
        seat_position=det.seat_position,
        review_status=det.review_status,
        reviewed_at=det.reviewed_at.isoformat() if det.reviewed_at else None,
        review_note=det.review_note,
        detected_at=det.detected_at.isoformat(),
    )


# --- 認証エンドポイント ---


@router.post("/auth/verify")
@limiter.limit("10/minute")
def verify_admin_token(
    request: Request,
    body: AdminAuthRequest,
) -> AdminAuthResponse:
    """Adminトークンの有効性を検証する。"""
    if not settings.admin_token:
        return AdminAuthResponse(valid=False)
    return AdminAuthResponse(valid=body.token == settings.admin_token)


# --- 閲覧エンドポイント (Admin認証必須) ---


@router.get("/detections")
def list_detections(
    session_id: int | None = None,
    member_id: int | None = None,
    status: str | None = Query(None, pattern="^(pending|approved|rejected)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin),
) -> dict:
    """居眠り検出結果の一覧を取得する。"""
    query = db.query(SleepingDetection)

    if session_id is not None:
        query = query.filter(SleepingDetection.session_id == session_id)
    if member_id is not None:
        query = query.filter(SleepingDetection.member_id == member_id)
    if status is not None:
        query = query.filter(SleepingDetection.review_status == status)

    total = query.count()
    detections = (
        query.order_by(SleepingDetection.detected_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {"total": total, "items": [_build_response(d, db) for d in detections]}


@router.get("/detections/{detection_id}")
def get_detection(
    detection_id: int,
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin),
) -> SleepingDetectionResponse:
    """居眠り検出の詳細を取得する。"""
    det = db.get(SleepingDetection, detection_id)
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")
    return _build_response(det, db)


# --- レビューエンドポイント (Admin認証必須) ---


@router.put("/detections/{detection_id}/review")
@limiter.limit("30/minute")
def review_detection(
    request: Request,
    detection_id: int,
    review: ReviewRequest,
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin),
) -> SleepingDetectionResponse:
    """居眠り検出を承認または却下し、該当議員のスコアを再計算する。"""
    if review.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="status must be 'approved' or 'rejected'",
        )

    det = db.get(SleepingDetection, detection_id)
    if not det:
        raise HTTPException(status_code=404, detail="Detection not found")

    prev_status = det.review_status
    det.review_status = review.status
    det.reviewed_at = datetime.now(UTC)
    det.review_note = review.note

    # レビュー時に議員を手動紐付け
    if review.member_id is not None:
        member = db.get(Member, review.member_id)
        if not member:
            raise HTTPException(status_code=400, detail="Member not found")
        det.member_id = review.member_id
        det.identified_by = "manual"

    db.commit()
    db.refresh(det)

    # ステータスが変わった場合、影響を受ける議員のスコアを再計算
    if prev_status != review.status and det.member_id:
        _recalculate_member_score(db, det.member_id, det.session_id)

    return _build_response(det, db)


# --- 統計エンドポイント ---


@router.get("/stats")
def get_sleeping_stats(
    session_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin),
) -> SleepingStatsResponse:
    """居眠り検出の統計を取得する。"""
    query = db.query(SleepingDetection)
    if session_id is not None:
        query = query.filter(SleepingDetection.session_id == session_id)

    total = query.count()
    pending = query.filter(SleepingDetection.review_status == "pending").count()
    approved = query.filter(SleepingDetection.review_status == "approved").count()
    rejected = query.filter(SleepingDetection.review_status == "rejected").count()

    members_with_incidents = (
        db.query(func.count(func.distinct(SleepingDetection.member_id)))
        .filter(
            SleepingDetection.review_status == "approved",
            SleepingDetection.member_id.isnot(None),
        )
        .scalar()
    ) or 0

    return SleepingStatsResponse(
        total_detections=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        members_with_incidents=members_with_incidents,
    )


@router.get("/members/{member_id}/incidents")
def get_member_incidents(
    member_id: int,
    session_id: int | None = None,
    db: Session = Depends(get_db),
    _admin: None = Depends(_require_admin),
) -> dict:
    """特定議員の承認済み居眠りインシデント一覧。"""
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    query = db.query(SleepingDetection).filter(
        SleepingDetection.member_id == member_id,
        SleepingDetection.review_status == "approved",
    )
    if session_id is not None:
        query = query.filter(SleepingDetection.session_id == session_id)

    incidents = query.order_by(SleepingDetection.start_time_sec).all()

    return {
        "member_id": member_id,
        "member_name": member.name,
        "total_incidents": len(incidents),
        "total_duration_sec": sum(i.duration_sec for i in incidents),
        "incidents": [
            {
                "id": i.id,
                "video_url": i.video_url,
                "meeting_name": i.meeting_name,
                "start_time_sec": i.start_time_sec,
                "duration_sec": i.duration_sec,
                "detection_type": i.detection_type,
                "screenshot_path": i.screenshot_path,
                "clip_path": i.clip_path,
            }
            for i in incidents
        ],
    }


def _recalculate_member_score(db: Session, member_id: int, session_id: int):
    """レビュー結果に応じて該当議員のスコアを再計算する。"""
    try:
        session = db.get(DietSession, session_id)
        if not session:
            return

        from app.services.scoring import compute_scores_for_session

        compute_scores_for_session(db, session.session_number)
        logger.info(
            f"Recalculated scores for session {session.session_number} "
            f"(triggered by sleeping review for member {member_id})"
        )
    except Exception:
        logger.exception("Failed to recalculate scores after sleeping review")
