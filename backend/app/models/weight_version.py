from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WeightVersion(Base):
    """スコアリング重みのバージョン管理。

    重みが変更されるたびに新しいレコードを作成する。
    scoring.py の DEFAULT_WEIGHTS と一致しているか CI で検証する。
    """

    __tablename__ = "weight_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    legislative_activity: Mapped[float] = mapped_column(Float, nullable=False)
    voting_behavior: Mapped[float] = mapped_column(Float, nullable=False)
    policy_influence: Mapped[float] = mapped_column(Float, nullable=False)
    transparency: Mapped[float] = mapped_column(Float, nullable=False)
    question_quality: Mapped[float] = mapped_column(Float, nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
