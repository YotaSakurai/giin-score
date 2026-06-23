"""Add committee_memberships and political_funds tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # committee_memberships
    op.create_table(
        "committee_memberships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("committee_name", sa.String(200), nullable=False),
        sa.Column("chamber", sa.String(20), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="委員"),
        sa.Column("committee_type", sa.String(20), nullable=False, server_default="常任"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["diet_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_committee_memberships_member_id", "committee_memberships", ["member_id"])
    op.create_index("ix_committee_session", "committee_memberships", ["session_id"])
    op.create_index(
        "uq_committee_member_session_name",
        "committee_memberships",
        ["member_id", "session_id", "committee_name"],
        unique=True,
    )

    # political_funds
    op.create_table(
        "political_funds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("report_year", sa.Integer(), nullable=False),
        sa.Column("organization_name", sa.String(200), nullable=False),
        sa.Column("total_income", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("individual_donations", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("corporate_donations", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("party_donations", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("party_subsidy", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("party_fee", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("fundraising_party", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("other_income", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("total_expenditure", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("personnel_expenses", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("office_expenses", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("political_activity", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("research_expenses", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("organization_expenses", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("other_expenses", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_political_funds_member_id", "political_funds", ["member_id"])
    op.create_index("ix_political_funds_year", "political_funds", ["report_year"])
    op.create_index(
        "uq_political_fund_member_year_org",
        "political_funds",
        ["member_id", "report_year", "organization_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_political_fund_member_year_org", "political_funds")
    op.drop_index("ix_political_funds_year", "political_funds")
    op.drop_index("ix_political_funds_member_id", "political_funds")
    op.drop_table("political_funds")

    op.drop_index("uq_committee_member_session_name", "committee_memberships")
    op.drop_index("ix_committee_session", "committee_memberships")
    op.drop_index("ix_committee_memberships_member_id", "committee_memberships")
    op.drop_table("committee_memberships")
