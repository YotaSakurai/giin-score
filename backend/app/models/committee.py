from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommitteeMembership(Base):
    """議員の委員会所属データ"""

    __tablename__ = "committee_memberships"
    __table_args__ = (
        UniqueConstraint(
            "member_id", "session_id", "committee_name",
            name="uq_committee_member_session_name",
        ),
        Index("ix_committee_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False, index=True
    )
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("diet_sessions.id"), nullable=False
    )
    committee_name: Mapped[str] = mapped_column(String(200), nullable=False)
    chamber: Mapped[str] = mapped_column(String(20), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="委員"
    )  # 委員長/理事/委員
    committee_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="常任"
    )  # 常任/特別/審査会/調査会
