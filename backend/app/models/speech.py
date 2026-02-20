from datetime import date

from sqlalchemy import Integer, String, ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Speech(Base):
    __tablename__ = "speeches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("diet_sessions.id"), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    meeting_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    speech_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    speech_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_chars: Mapped[int] = mapped_column(Integer, default=0)
    speech_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("DietSession", back_populates="speeches")
    member = relationship("Member", back_populates="speeches")
