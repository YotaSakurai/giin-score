from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserReview(Base):
    __tablename__ = "user_reviews"
    __table_args__ = (
        UniqueConstraint("member_id", "reviewer_id", name="uq_member_reviewer"),
        Index("ix_user_reviews_member_id", "member_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(String(36), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 5軸スコア (0-100)
    legislative_activity: Mapped[float] = mapped_column(Float, default=50.0)
    voting_behavior: Mapped[float] = mapped_column(Float, default=50.0)
    policy_influence: Mapped[float] = mapped_column(Float, default=50.0)
    transparency: Mapped[float] = mapped_column(Float, default=50.0)
    question_quality: Mapped[float] = mapped_column(Float, default=50.0)
    total: Mapped[float] = mapped_column(Float, default=50.0)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    like_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    member = relationship("Member")
    likes = relationship(
        "ReviewLike", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewLike(Base):
    __tablename__ = "review_likes"
    __table_args__ = (
        UniqueConstraint("review_id", "liker_id", name="uq_review_liker"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_reviews.id"), nullable=False
    )
    liker_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    review = relationship("UserReview", back_populates="likes")
