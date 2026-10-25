"""driver links and order events

Revision ID: 28cfd55d808f
Revises: 5d7a57911503
Create Date: 2026-10-25 19:59:05.067556
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '28cfd55d808f'
down_revision: Union[str, None] = '5d7a57911503'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('order_events',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('order_id', sa.String(length=36), nullable=False),
    sa.Column('driver_id', sa.String(length=36), nullable=True),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('note', sa.String(length=2000), nullable=False),
    sa.Column('photo', sa.LargeBinary(), nullable=True),
    sa.Column('photo_type', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('order_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_order_events_order_id'), ['order_id'], unique=False)

    with op.batch_alter_table('drivers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('access_token_hash', sa.String(length=64), nullable=True))
        batch_op.create_unique_constraint('uq_drivers_access_token_hash', ['access_token_hash'])

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('execution_status', sa.String(length=20), nullable=True))



def downgrade() -> None:
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('execution_status')

    with op.batch_alter_table('drivers', schema=None) as batch_op:
        batch_op.drop_constraint('uq_drivers_access_token_hash', type_='unique')
        batch_op.drop_column('access_token_hash')

    with op.batch_alter_table('order_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_order_events_order_id'))

    op.drop_table('order_events')
