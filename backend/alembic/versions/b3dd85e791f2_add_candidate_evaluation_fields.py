"""add candidate evaluation fields to wardrobe_items

Revision ID: b3dd85e791f2
Revises: a2cc4ce6134e
Create Date: 2026-08-28 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3dd85e791f2'
down_revision: Union[str, Sequence[str], None] = 'a2cc4ce6134e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('wardrobe_items', sa.Column('price', sa.Float(), nullable=True))
    op.add_column('wardrobe_items', sa.Column('tryon_render_url', sa.String(length=1024), nullable=True))
    op.add_column('wardrobe_items', sa.Column('fit_tightness', sa.String(length=100), nullable=True))
    op.add_column('wardrobe_items', sa.Column('silhouette', sa.String(length=100), nullable=True))
    op.add_column('wardrobe_items', sa.Column('duplicate_match_item_id', sa.Integer(), sa.ForeignKey('wardrobe_items.id'), nullable=True))
    op.add_column('wardrobe_items', sa.Column('duplicate_similarity_pct', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('wardrobe_items', 'duplicate_similarity_pct')
    op.drop_column('wardrobe_items', 'duplicate_match_item_id')
    op.drop_column('wardrobe_items', 'silhouette')
    op.drop_column('wardrobe_items', 'fit_tightness')
    op.drop_column('wardrobe_items', 'tryon_render_url')
    op.drop_column('wardrobe_items', 'price')
