"""Add speech quality scoring tables and columns

Revision ID: 003
Revises: 002
Create Date: 2026-03-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # speech_quality_scores テーブル作成
    op.create_table(
        "speech_quality_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("speech_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("policy_relevance", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("constructiveness", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("expertise", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("national_interest", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("overall_quality", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("analysis_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["speech_id"], ["speeches.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["diet_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("speech_id", name="uq_speech_quality_speech"),
    )
    op.create_index("ix_speech_quality_member_id", "speech_quality_scores", ["member_id"])
    op.create_index("ix_speech_quality_session_id", "speech_quality_scores", ["session_id"])
    op.create_index("ix_speech_quality_speech_id", "speech_quality_scores", ["speech_id"])

    # member_scores に question_quality カラム追加
    op.add_column(
        "member_scores",
        sa.Column("question_quality_raw", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "member_scores",
        sa.Column("question_quality", sa.Float(), server_default="0.0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("member_scores", "question_quality")
    op.drop_column("member_scores", "question_quality_raw")
    op.drop_index("ix_speech_quality_speech_id", "speech_quality_scores")
    op.drop_index("ix_speech_quality_session_id", "speech_quality_scores")
    op.drop_index("ix_speech_quality_member_id", "speech_quality_scores")
    op.drop_table("speech_quality_scores")
