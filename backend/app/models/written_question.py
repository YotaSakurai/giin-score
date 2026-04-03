import sqlalchemy as sa
from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WrittenQuestion(Base):
    """質問主意書"""

    __tablename__ = "written_questions"
    __table_args__ = (
        sa.UniqueConstraint(
            "session_id", "chamber", "question_number",
            name="uq_written_questions_session_chamber_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("diet_sessions.id"), nullable=False, index=True
    )
    member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=True, index=True
    )
    chamber: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # representatives/councillors
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_date: Mapped[sa.Date | None] = mapped_column(Date, nullable=True)
    answer_date: Mapped[sa.Date | None] = mapped_column(Date, nullable=True)
    question_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_answer: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )

    session = relationship("DietSession", backref="written_questions")
    member = relationship("Member", backref="written_questions")
