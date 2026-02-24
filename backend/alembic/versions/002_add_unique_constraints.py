"""Add unique constraints for data integrity

Revision ID: 002
Revises: 001
Create Date: 2026-02-25
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # members: 同一人物の重複防止
    op.create_unique_constraint("uq_members_name_chamber", "members", ["name", "chamber"])

    # speeches: 同一発言の重複防止
    op.create_index("ix_speeches_speech_url", "speeches", ["speech_url"], unique=False)

    # vote_records: 同一投票の重複防止
    op.create_unique_constraint(
        "uq_vote_records_result_member", "vote_records", ["vote_result_id", "member_id"]
    )

    # bill_sponsors: 同一提出者の重複防止
    op.create_unique_constraint(
        "uq_bill_sponsors_bill_member", "bill_sponsors", ["bill_id", "member_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_bill_sponsors_bill_member", "bill_sponsors", type_="unique")
    op.drop_constraint("uq_vote_records_result_member", "vote_records", type_="unique")
    op.drop_index("ix_speeches_speech_url", "speeches")
    op.drop_constraint("uq_members_name_chamber", "members", type_="unique")
