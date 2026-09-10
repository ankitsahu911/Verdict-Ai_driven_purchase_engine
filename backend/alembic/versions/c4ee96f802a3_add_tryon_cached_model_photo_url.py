"""add tryon_cached_model_photo_url to wardrobe_items and model_photo_url to users

Revision ID: c4ee96f802a3
Revises: b3dd85e791f2
Create Date: 2026-09-06 20:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4ee96f802a3'
down_revision: Union[str, Sequence[str], None] = 'b3dd85e791f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('wardrobe_items', sa.Column('tryon_cached_model_photo_url', sa.String(length=1024), nullable=True))
    op.add_column('users', sa.Column('model_photo_url', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'model_photo_url')
    op.drop_column('wardrobe_items', 'tryon_cached_model_photo_url')
