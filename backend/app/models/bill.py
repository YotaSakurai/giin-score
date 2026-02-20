from sqlalchemy import Integer, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("diet_sessions.id"), nullable=False, index=True)
    bill_kind: Mapped[str] = mapped_column(String(50), nullable=False)  # 閣法/衆法/参法
    bill_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 審議中/成立/否決/廃案/継続
    result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proposer_type: Mapped[str | None] = mapped_column(String(30), nullable=True)  # cabinet/member
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("DietSession", back_populates="bills")
    sponsors = relationship("BillSponsor", back_populates="bill", cascade="all, delete-orphan")
    vote_results = relationship("VoteResult", back_populates="bill", cascade="all, delete-orphan")


class BillSponsor(Base):
    __tablename__ = "bill_sponsors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    sponsor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # primary/co-sponsor

    bill = relationship("Bill", back_populates="sponsors")
    member = relationship("Member", back_populates="bill_sponsorships")
