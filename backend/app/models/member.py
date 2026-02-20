from sqlalchemy import Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name_reading: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chamber: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # representatives/councillors
    party: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    faction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role_category: Mapped[str | None] = mapped_column(
        String(30), nullable=True, index=True
    )  # cabinet/ruling_junior/opposition_senior/opposition_junior/chair
    external_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    speeches = relationship("Speech", back_populates="member")
    vote_records = relationship("VoteRecord", back_populates="member")
    bill_sponsorships = relationship("BillSponsor", back_populates="member")
    scores = relationship("MemberScore", back_populates="member")
