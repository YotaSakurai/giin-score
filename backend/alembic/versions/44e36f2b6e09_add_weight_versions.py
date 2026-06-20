"""add weight_versions

Revision ID: 44e36f2b6e09
Revises: 6aec7c9a9de7
Create Date: 2026-05-14 16:38:13.662962
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44e36f2b6e09'
down_revision: Union[str, None] = '6aec7c9a9de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('weight_versions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('version', sa.String(length=50), nullable=False),
    sa.Column('legislative_activity', sa.Float(), nullable=False),
    sa.Column('voting_behavior', sa.Float(), nullable=False),
    sa.Column('policy_influence', sa.Float(), nullable=False),
    sa.Column('transparency', sa.Float(), nullable=False),
    sa.Column('question_quality', sa.Float(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('version')
    )


def downgrade() -> None:
    op.drop_table('weight_versions')
