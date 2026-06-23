"""居眠り検出モデル

国会中継動画から検出された居眠りシーンを管理する。
AI検出 → 管理者レビュー → スコア反映 のフローを想定。
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SleepingDetection(Base):
    __tablename__ = "sleeping_detections"
    __table_args__ = (
        Index("ix_sleeping_detections_member_session", "member_id", "session_id"),
        Index("ix_sleeping_detections_status", "review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=True, index=True
    )
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("diet_sessions.id"), nullable=False, index=True
    )

    # 動画情報
    video_url: Mapped[str] = mapped_column(String(500), nullable=False)
    video_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    meeting_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 検出タイミング
    start_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_time_sec: Mapped[float] = mapped_column(Float, nullable=False)
    duration_sec: Mapped[float] = mapped_column(Float, nullable=False)

    # 検出詳細
    detection_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # head_forward / head_backward
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    head_angle_avg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 証拠ファイル
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    clip_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 議員特定情報（顔認識/座席マッピング）
    identified_by: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # face_recognition / seat_mapping / manual
    identification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    seat_position: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # レビュー
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending / approved / rejected
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # タイムスタンプ
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    member = relationship("Member")
    session = relationship("DietSession")
