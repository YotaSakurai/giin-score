from sqlalchemy import Integer, Float, String, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MemberScore(Base):
    __tablename__ = "member_scores"
    __table_args__ = (
        UniqueConstraint("member_id", "session_id", name="uq_member_session_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("diet_sessions.id"), nullable=False, index=True)

    # Raw scores
    legislative_activity_raw: Mapped[float] = mapped_column(Float, default=0.0)
    voting_behavior_raw: Mapped[float] = mapped_column(Float, default=0.0)
    policy_influence_raw: Mapped[float] = mapped_column(Float, default=0.0)
    transparency_raw: Mapped[float] = mapped_column(Float, default=0.0)

    # Normalized scores (0-100, percentile rank)
    legislative_activity: Mapped[float] = mapped_column(Float, default=0.0)
    voting_behavior: Mapped[float] = mapped_column(Float, default=0.0)
    policy_influence: Mapped[float] = mapped_column(Float, default=0.0)
    transparency: Mapped[float] = mapped_column(Float, default=0.0)

    # Total and grade
    total: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[str] = mapped_column(String(2), default="F")

    # Detailed breakdown
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    member = relationship("Member", back_populates="scores")
    session = relationship("DietSession", back_populates="scores")
