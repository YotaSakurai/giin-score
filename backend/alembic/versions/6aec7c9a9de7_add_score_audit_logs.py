"""add score_audit_logs

Revision ID: 6aec7c9a9de7
Revises: fb4deeef532b
Create Date: 2026-05-14 16:33:53.975808
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6aec7c9a9de7'
down_revision: Union[str, None] = 'fb4deeef532b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('score_audit_logs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('member_id', sa.Integer(), nullable=False),
    sa.Column('session_number', sa.Integer(), nullable=False),
    sa.Column('prev_total', sa.Float(), nullable=True),
    sa.Column('prev_grade', sa.String(length=2), nullable=True),
    sa.Column('prev_legislative_activity', sa.Float(), nullable=True),
    sa.Column('prev_voting_behavior', sa.Float(), nullable=True),
    sa.Column('prev_policy_influence', sa.Float(), nullable=True),
    sa.Column('prev_transparency', sa.Float(), nullable=True),
    sa.Column('prev_question_quality', sa.Float(), nullable=True),
    sa.Column('new_total', sa.Float(), nullable=False),
    sa.Column('new_grade', sa.String(length=2), nullable=False),
    sa.Column('new_legislative_activity', sa.Float(), nullable=False),
    sa.Column('new_voting_behavior', sa.Float(), nullable=False),
    sa.Column('new_policy_influence', sa.Float(), nullable=False),
    sa.Column('new_transparency', sa.Float(), nullable=False),
    sa.Column('new_question_quality', sa.Float(), nullable=False),
    sa.Column('diff_total', sa.Float(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('weights_version', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_score_audit_logs_member_id'), 'score_audit_logs', ['member_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_score_audit_logs_member_id'), table_name='score_audit_logs')
    op.drop_table('score_audit_logs')
