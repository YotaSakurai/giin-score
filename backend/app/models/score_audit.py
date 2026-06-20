from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScoreAuditLog(Base):
    """スコア変更の監査ログ。

    スコアリングパイプライン実行時に、各議員のスコアが変更された場合の
    before/after を記録する。異常な変動の追跡・原因分析に使用。
    """

    __tablename__ = "score_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # before
    prev_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    prev_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    prev_legislative_activity: Mapped[float | None] = mapped_column(Float, nullable=True)
    prev_voting_behavior: Mapped[float | None] = mapped_column(Float, nullable=True)
    prev_policy_influence: Mapped[float | None] = mapped_column(Float, nullable=True)
    prev_transparency: Mapped[float | None] = mapped_column(Float, nullable=True)
    prev_question_quality: Mapped[float | None] = mapped_column(Float, nullable=True)

    # after
    new_total: Mapped[float] = mapped_column(Float, nullable=False)
    new_grade: Mapped[str] = mapped_column(String(2), nullable=False)
    new_legislative_activity: Mapped[float] = mapped_column(Float, nullable=False)
    new_voting_behavior: Mapped[float] = mapped_column(Float, nullable=False)
    new_policy_influence: Mapped[float] = mapped_column(Float, nullable=False)
    new_transparency: Mapped[float] = mapped_column(Float, nullable=False)
    new_question_quality: Mapped[float] = mapped_column(Float, nullable=False)

    # メタ
    diff_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="scheduled_pipeline")
    weights_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
