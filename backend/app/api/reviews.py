from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.review import ReviewLike, UserReview
from app.schemas.review import (
    LikeToggleRequest,
    ReviewCreate,
    ReviewResponse,
    ReviewSummary,
    ReviewUpdate,
)

router = APIRouter(tags=["reviews"])

limiter = Limiter(key_func=get_remote_address)


def _compute_total(la: float, vb: float, pi: float, tr: float, qq: float) -> float:
    return (la + vb + pi + tr + qq) / 5


def _to_response(review: UserReview, liker_id: str | None, db: Session = None) -> dict:
    is_liked = False
    if liker_id and hasattr(review, "likes") and review.likes is not None:
        # selectinload済みの場合はメモリで判定 (N+1回避)
        is_liked = any(like.liker_id == liker_id for like in review.likes)
    elif liker_id and db is not None:
        # フォールバック: 個別クエリ
        is_liked = (
            db.query(ReviewLike)
            .filter(ReviewLike.review_id == review.id, ReviewLike.liker_id == liker_id)
            .first()
            is not None
        )
    return {
        "id": review.id,
        "member_id": review.member_id,
        "reviewer_id": review.reviewer_id,
        "display_name": review.display_name,
        "legislative_activity": review.legislative_activity,
        "voting_behavior": review.voting_behavior,
        "policy_influence": review.policy_influence,
        "transparency": review.transparency,
        "question_quality": review.question_quality,
        "total": review.total,
        "comment": review.comment,
        "like_count": review.like_count,
        "is_liked": is_liked,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


@router.get("/members/{member_id}/reviews")
@limiter.limit("60/minute")
def get_reviews(
    request: Request,
    member_id: int,
    sort: str = Query("likes", pattern="^(likes|newest)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    liker_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    base_query = db.query(UserReview).filter(UserReview.member_id == member_id)

    total = base_query.count()

    if sort == "likes":
        base_query = base_query.order_by(UserReview.like_count.desc(), UserReview.created_at.desc())
    else:
        base_query = base_query.order_by(UserReview.created_at.desc())

    reviews = (
        base_query.options(selectinload(UserReview.likes))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "items": [_to_response(r, liker_id, db) for r in reviews],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@router.get("/members/{member_id}/review-summary", response_model=ReviewSummary)
@limiter.limit("60/minute")
def get_review_summary(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db),
):
    result = (
        db.query(
            func.count(UserReview.id).label("review_count"),
            func.coalesce(func.avg(UserReview.legislative_activity), 0).label("avg_la"),
            func.coalesce(func.avg(UserReview.voting_behavior), 0).label("avg_vb"),
            func.coalesce(func.avg(UserReview.policy_influence), 0).label("avg_pi"),
            func.coalesce(func.avg(UserReview.transparency), 0).label("avg_tr"),
            func.coalesce(func.avg(UserReview.question_quality), 0).label("avg_qq"),
            func.coalesce(func.avg(UserReview.total), 0).label("avg_total"),
        )
        .filter(UserReview.member_id == member_id)
        .first()
    )

    return ReviewSummary(
        member_id=member_id,
        review_count=result.review_count if result else 0,
        average_legislative_activity=round(float(result.avg_la), 1) if result else 0,
        average_voting_behavior=round(float(result.avg_vb), 1) if result else 0,
        average_policy_influence=round(float(result.avg_pi), 1) if result else 0,
        average_transparency=round(float(result.avg_tr), 1) if result else 0,
        average_question_quality=round(float(result.avg_qq), 1) if result else 0,
        average_total=round(float(result.avg_total), 1) if result else 0,
    )


@router.post("/members/{member_id}/reviews", response_model=ReviewResponse)
@limiter.limit("10/minute")
def create_review(
    request: Request,
    member_id: int,
    body: ReviewCreate,
    db: Session = Depends(get_db),
):
    total = _compute_total(
        body.legislative_activity,
        body.voting_behavior,
        body.policy_influence,
        body.transparency,
        body.question_quality,
    )

    # Upsert: 同じ member_id + reviewer_id があれば更新
    existing = (
        db.query(UserReview)
        .filter(
            UserReview.member_id == member_id,
            UserReview.reviewer_id == body.reviewer_id,
        )
        .first()
    )

    if existing:
        existing.display_name = body.display_name
        existing.legislative_activity = body.legislative_activity
        existing.voting_behavior = body.voting_behavior
        existing.policy_influence = body.policy_influence
        existing.transparency = body.transparency
        existing.question_quality = body.question_quality
        existing.total = total
        existing.comment = body.comment
        db.commit()
        db.refresh(existing)
        return _to_response(existing, body.reviewer_id, db)

    review = UserReview(
        member_id=member_id,
        reviewer_id=body.reviewer_id,
        display_name=body.display_name,
        legislative_activity=body.legislative_activity,
        voting_behavior=body.voting_behavior,
        policy_influence=body.policy_influence,
        transparency=body.transparency,
        question_quality=body.question_quality,
        total=total,
        comment=body.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return _to_response(review, body.reviewer_id, db)


@router.put("/reviews/{review_id}", response_model=ReviewResponse)
@limiter.limit("10/minute")
def update_review(
    request: Request,
    review_id: int,
    body: ReviewUpdate,
    db: Session = Depends(get_db),
):
    review = db.query(UserReview).filter(UserReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.reviewer_id != body.reviewer_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if body.display_name is not None:
        review.display_name = body.display_name
    if body.legislative_activity is not None:
        review.legislative_activity = body.legislative_activity
    if body.voting_behavior is not None:
        review.voting_behavior = body.voting_behavior
    if body.policy_influence is not None:
        review.policy_influence = body.policy_influence
    if body.transparency is not None:
        review.transparency = body.transparency
    if body.question_quality is not None:
        review.question_quality = body.question_quality
    if body.comment is not None:
        review.comment = body.comment

    review.total = _compute_total(
        review.legislative_activity,
        review.voting_behavior,
        review.policy_influence,
        review.transparency,
        review.question_quality,
    )
    db.commit()
    db.refresh(review)
    return _to_response(review, body.reviewer_id, db)


@router.delete("/reviews/{review_id}")
@limiter.limit("10/minute")
def delete_review(
    request: Request,
    review_id: int,
    reviewer_id: str = Query(...),
    db: Session = Depends(get_db),
):
    review = db.query(UserReview).filter(UserReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.reviewer_id != reviewer_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(review)
    db.commit()
    return {"ok": True}


@router.post("/reviews/{review_id}/like")
@limiter.limit("30/minute")
def toggle_like(
    request: Request,
    review_id: int,
    body: LikeToggleRequest,
    db: Session = Depends(get_db),
):
    review = db.query(UserReview).filter(UserReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    existing = (
        db.query(ReviewLike)
        .filter(
            ReviewLike.review_id == review_id,
            ReviewLike.liker_id == body.liker_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        review.like_count = max(0, review.like_count - 1)
    else:
        like = ReviewLike(review_id=review_id, liker_id=body.liker_id)
        db.add(like)
        review.like_count = review.like_count + 1

    db.commit()
    db.refresh(review)
    return {"like_count": review.like_count, "is_liked": existing is None}
