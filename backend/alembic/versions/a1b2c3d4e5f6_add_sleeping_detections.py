"""add sleeping_detections table

Revision ID: a1b2c3d4e5f6
Revises: 44e36f2b6e09
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "44e36f2b6e09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sleeping_detections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("video_url", sa.String(500), nullable=False),
        sa.Column("video_date", sa.DateTime(), nullable=True),
        sa.Column("meeting_name", sa.String(200), nullable=True),
        sa.Column("start_time_sec", sa.Float(), nullable=False),
        sa.Column("end_time_sec", sa.Float(), nullable=False),
        sa.Column("duration_sec", sa.Float(), nullable=False),
        sa.Column("detection_type", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("head_angle_avg", sa.Float(), nullable=True),
        sa.Column("screenshot_path", sa.String(500), nullable=True),
        sa.Column("clip_path", sa.String(500), nullable=True),
        sa.Column("identified_by", sa.String(30), nullable=True),
        sa.Column("identification_confidence", sa.Float(), nullable=True),
        sa.Column("seat_position", sa.String(50), nullable=True),
        sa.Column(
            "review_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["diet_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sleeping_detections_member_id", "sleeping_detections", ["member_id"])
    op.create_index("ix_sleeping_detections_session_id", "sleeping_detections", ["session_id"])
    op.create_index(
        "ix_sleeping_detections_member_session",
        "sleeping_detections",
        ["member_id", "session_id"],
    )
    op.create_index(
        "ix_sleeping_detections_status",
        "sleeping_detections",
        ["review_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_sleeping_detections_status", "sleeping_detections")
    op.drop_index("ix_sleeping_detections_member_session", "sleeping_detections")
    op.drop_index("ix_sleeping_detections_session_id", "sleeping_detections")
    op.drop_index("ix_sleeping_detections_member_id", "sleeping_detections")
    op.drop_table("sleeping_detections")
