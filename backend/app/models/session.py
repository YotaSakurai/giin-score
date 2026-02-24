from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DietSession(Base):
    __tablename__ = "diet_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # 通常/臨時/特別
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    bills = relationship("Bill", back_populates="session")
    speeches = relationship("Speech", back_populates="session")
    scores = relationship("MemberScore", back_populates="session")
