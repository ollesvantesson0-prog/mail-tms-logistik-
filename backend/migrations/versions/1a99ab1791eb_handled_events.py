"""handled events

Revision ID: 1a99ab1791eb
Revises: 28cfd55d808f
Create Date: 2026-10-25 20:06:27.294892
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1a99ab1791eb'
down_revision: Union[str, None] = '28cfd55d808f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('order_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('order_events', schema=None) as batch_op:
        batch_op.drop_column('handled_at')

