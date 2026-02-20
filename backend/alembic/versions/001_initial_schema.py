"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diet_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_number"),
    )
    op.create_index("ix_diet_sessions_session_number", "diet_sessions", ["session_number"])

    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_reading", sa.String(100), nullable=True),
        sa.Column("chamber", sa.String(20), nullable=False),
        sa.Column("party", sa.String(100), nullable=True),
        sa.Column("faction", sa.String(100), nullable=True),
        sa.Column("district", sa.String(200), nullable=True),
        sa.Column("role_category", sa.String(30), nullable=True),
        sa.Column("external_ids", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_members_name", "members", ["name"])
    op.create_index("ix_members_chamber", "members", ["chamber"])
    op.create_index("ix_members_party", "members", ["party"])
    op.create_index("ix_members_role_category", "members", ["role_category"])

    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("bill_kind", sa.String(50), nullable=False),
        sa.Column("bill_number", sa.String(30), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("result", sa.String(50), nullable=True),
        sa.Column("proposer_type", sa.String(30), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["diet_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bills_session_id", "bills", ["session_id"])

    op.create_table(
        "bill_sponsors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("sponsor_type", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bill_sponsors_bill_id", "bill_sponsors", ["bill_id"])
    op.create_index("ix_bill_sponsors_member_id", "bill_sponsors", ["member_id"])

    op.create_table(
        "vote_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("chamber", sa.String(20), nullable=False),
        sa.Column("ayes", sa.Integer(), default=0),
        sa.Column("nays", sa.Integer(), default=0),
        sa.Column("result", sa.String(30), nullable=True),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vote_results_bill_id", "vote_results", ["bill_id"])

    op.create_table(
        "vote_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vote_result_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("vote", sa.String(10), nullable=False),
        sa.ForeignKeyConstraint(["vote_result_id"], ["vote_results.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vote_records_vote_result_id", "vote_records", ["vote_result_id"])
    op.create_index("ix_vote_records_member_id", "vote_records", ["member_id"])

    op.create_table(
        "speeches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("meeting_name", sa.String(200), nullable=True),
        sa.Column("speech_date", sa.Date(), nullable=True),
        sa.Column("speech_text", sa.Text(), nullable=True),
        sa.Column("speech_chars", sa.Integer(), default=0),
        sa.Column("speech_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["diet_sessions.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_speeches_session_id", "speeches", ["session_id"])
    op.create_index("ix_speeches_member_id", "speeches", ["member_id"])

    op.create_table(
        "member_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("legislative_activity_raw", sa.Float(), default=0.0),
        sa.Column("voting_behavior_raw", sa.Float(), default=0.0),
        sa.Column("policy_influence_raw", sa.Float(), default=0.0),
        sa.Column("transparency_raw", sa.Float(), default=0.0),
        sa.Column("legislative_activity", sa.Float(), default=0.0),
        sa.Column("voting_behavior", sa.Float(), default=0.0),
        sa.Column("policy_influence", sa.Float(), default=0.0),
        sa.Column("transparency", sa.Float(), default=0.0),
        sa.Column("total", sa.Float(), default=0.0),
        sa.Column("grade", sa.String(2), default="F"),
        sa.Column("breakdown", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["diet_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("member_id", "session_id", name="uq_member_session_score"),
    )
    op.create_index("ix_member_scores_member_id", "member_scores", ["member_id"])
    op.create_index("ix_member_scores_session_id", "member_scores", ["session_id"])

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_name", sa.String(100), nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("records_processed", sa.Integer(), default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    op.drop_table("member_scores")
    op.drop_table("speeches")
    op.drop_table("vote_records")
    op.drop_table("vote_results")
    op.drop_table("bill_sponsors")
    op.drop_table("bills")
    op.drop_table("members")
    op.drop_table("diet_sessions")
