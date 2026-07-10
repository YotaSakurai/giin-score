from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PoliticalFund(Base):
    """議員関連政治団体の収支集約データ"""

    __tablename__ = "political_funds"
    __table_args__ = (
        UniqueConstraint(
            "member_id",
            "report_year",
            "organization_name",
            name="uq_political_fund_member_year_org",
        ),
        Index("ix_political_funds_year", "report_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False, index=True
    )
    report_year: Mapped[int] = mapped_column(Integer, nullable=False)
    organization_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # 収入
    total_income: Mapped[float] = mapped_column(Float, default=0.0)
    individual_donations: Mapped[float] = mapped_column(Float, default=0.0)
    corporate_donations: Mapped[float] = mapped_column(Float, default=0.0)
    party_donations: Mapped[float] = mapped_column(Float, default=0.0)
    party_subsidy: Mapped[float] = mapped_column(Float, default=0.0)
    party_fee: Mapped[float] = mapped_column(Float, default=0.0)
    fundraising_party: Mapped[float] = mapped_column(Float, default=0.0)
    other_income: Mapped[float] = mapped_column(Float, default=0.0)

    # 支出
    total_expenditure: Mapped[float] = mapped_column(Float, default=0.0)
    personnel_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    office_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    political_activity: Mapped[float] = mapped_column(Float, default=0.0)
    research_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    organization_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    other_expenses: Mapped[float] = mapped_column(Float, default=0.0)

    # データソース
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
