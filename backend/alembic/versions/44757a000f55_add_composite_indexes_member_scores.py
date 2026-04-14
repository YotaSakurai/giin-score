"""add_composite_indexes_member_scores

Revision ID: 44757a000f55
Revises: 81fb521a982a
Create Date: 2026-04-14 14:06:11.941214
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '44757a000f55'
down_revision: Union[str, None] = '81fb521a982a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_member_scores_session_grade', 'member_scores', ['session_id', 'grade'], unique=False)
    op.create_index('ix_member_scores_session_total', 'member_scores', ['session_id', 'total'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_member_scores_session_total', table_name='member_scores')
    op.drop_index('ix_member_scores_session_grade', table_name='member_scores')
