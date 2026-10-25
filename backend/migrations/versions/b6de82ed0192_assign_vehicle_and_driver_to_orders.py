"""assign vehicle and driver to orders

Revision ID: b6de82ed0192
Revises: feaefccd6f60
Create Date: 2026-10-25 16:41:46.950848
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6de82ed0192'
down_revision: Union[str, None] = 'feaefccd6f60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vehicle_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('driver_id', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_orders_driver_id'), ['driver_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_orders_vehicle_id'), ['vehicle_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_orders_vehicle_id_vehicles', 'vehicles', ['vehicle_id'], ['id'], ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_orders_driver_id_drivers', 'drivers', ['driver_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint('fk_orders_driver_id_drivers', type_='foreignkey')
        batch_op.drop_constraint('fk_orders_vehicle_id_vehicles', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_orders_vehicle_id'))
        batch_op.drop_index(batch_op.f('ix_orders_driver_id'))
        batch_op.drop_column('driver_id')
        batch_op.drop_column('vehicle_id')
