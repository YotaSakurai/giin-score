from sqlalchemy import Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SpeechQualityScore(Base):
    __tablename__ = "speech_quality_scores"
    __table_args__ = (UniqueConstraint("speech_id", name="uq_speech_quality_speech"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    speech_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("speeches.id"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False, index=True
    )
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("diet_sessions.id"), nullable=False, index=True
    )

    # 4観点スコア (0-100)
    policy_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    constructiveness: Mapped[float] = mapped_column(Float, default=0.0)
    expertise: Mapped[float] = mapped_column(Float, default=0.0)
    national_interest: Mapped[float] = mapped_column(Float, default=0.0)

    # 総合品質スコア (4観点の平均)
    overall_quality: Mapped[float] = mapped_column(Float, default=0.0)

    # LLM分析の要約
    analysis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    speech = relationship("Speech", backref="quality_score")
    member = relationship("Member")
    session = relationship("DietSession")
