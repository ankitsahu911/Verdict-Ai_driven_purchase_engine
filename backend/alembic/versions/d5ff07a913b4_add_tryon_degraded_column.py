"""add tryon_degraded column to wardrobe_items

Revision ID: d5ff07a913b4
Revises: c4ee96f802a3
Create Date: 2026-09-06 21:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5ff07a913b4'
down_revision: Union[str, Sequence[str], None] = 'c4ee96f802a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('wardrobe_items', sa.Column('tryon_degraded', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('wardrobe_items', 'tryon_degraded')
