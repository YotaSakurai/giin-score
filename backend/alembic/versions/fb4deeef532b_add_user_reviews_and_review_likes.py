"""add user_reviews and review_likes

Revision ID: fb4deeef532b
Revises: 44757a000f55
Create Date: 2026-04-29 11:22:03.381038
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb4deeef532b'
down_revision: Union[str, None] = '44757a000f55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_reviews',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('member_id', sa.Integer(), nullable=False),
    sa.Column('reviewer_id', sa.String(length=36), nullable=False),
    sa.Column('display_name', sa.String(length=50), nullable=True),
    sa.Column('legislative_activity', sa.Float(), nullable=False),
    sa.Column('voting_behavior', sa.Float(), nullable=False),
    sa.Column('policy_influence', sa.Float(), nullable=False),
    sa.Column('transparency', sa.Float(), nullable=False),
    sa.Column('question_quality', sa.Float(), nullable=False),
    sa.Column('total', sa.Float(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('like_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('member_id', 'reviewer_id', name='uq_member_reviewer')
    )
    op.create_index('ix_user_reviews_member_id', 'user_reviews', ['member_id'], unique=False)
    op.create_table('review_likes',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('review_id', sa.Integer(), nullable=False),
    sa.Column('liker_id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['review_id'], ['user_reviews.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('review_id', 'liker_id', name='uq_review_liker')
    )


def downgrade() -> None:
    op.drop_table('review_likes')
    op.drop_index('ix_user_reviews_member_id', table_name='user_reviews')
    op.drop_table('user_reviews')
