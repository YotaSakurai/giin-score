from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VoteResult(Base):
    __tablename__ = "vote_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    chamber: Mapped[str] = mapped_column(String(20), nullable=False)  # representatives/councillors
    ayes: Mapped[int] = mapped_column(Integer, default=0)
    nays: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 可決/否決

    bill = relationship("Bill", back_populates="vote_results")
    records = relationship("VoteRecord", back_populates="vote_result", cascade="all, delete-orphan")


class VoteRecord(Base):
    __tablename__ = "vote_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vote_result_id: Mapped[int] = mapped_column(Integer, ForeignKey("vote_results.id"), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    vote: Mapped[str] = mapped_column(String(10), nullable=False)  # aye/nay/abstain/absent

    vote_result = relationship("VoteResult", back_populates="records")
    member = relationship("Member", back_populates="vote_records")
