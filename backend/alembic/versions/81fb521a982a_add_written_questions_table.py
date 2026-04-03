"""add written_questions table

Revision ID: 81fb521a982a
Revises: 003
Create Date: 2026-04-02 15:34:20.469646
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "81fb521a982a"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("written_questions",
    sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    sa.Column("session_id", sa.Integer(), nullable=False),
    sa.Column("member_id", sa.Integer(), nullable=True),
    sa.Column("chamber", sa.String(length=20), nullable=False),
    sa.Column("question_number", sa.Integer(), nullable=False),
    sa.Column("title", sa.Text(), nullable=False),
    sa.Column("submitted_date", sa.Date(), nullable=True),
    sa.Column("answer_date", sa.Date(), nullable=True),
    sa.Column("question_url", sa.Text(), nullable=True),
    sa.Column("answer_url", sa.Text(), nullable=True),
    sa.Column("has_answer", sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(["member_id"], ["members.id"], ),
    sa.ForeignKeyConstraint(["session_id"], ["diet_sessions.id"], ),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("session_id", "chamber", "question_number", name="uq_written_questions_session_chamber_number")
    )
    op.create_index(op.f("ix_written_questions_chamber"), "written_questions", ["chamber"], unique=False)
    op.create_index(op.f("ix_written_questions_member_id"), "written_questions", ["member_id"], unique=False)
    op.create_index(op.f("ix_written_questions_session_id"), "written_questions", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_written_questions_session_id"), table_name="written_questions")
    op.drop_index(op.f("ix_written_questions_member_id"), table_name="written_questions")
    op.drop_index(op.f("ix_written_questions_chamber"), table_name="written_questions")
    op.drop_table("written_questions")
