"""vehicle and driver capabilities

Revision ID: 5d7a57911503
Revises: b6de82ed0192
Create Date: 2026-10-25 19:43:29.020886
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5d7a57911503'
down_revision: Union[str, None] = 'b6de82ed0192'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('drivers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('has_adr_license', sa.Boolean(), server_default=sa.false(), nullable=False))

    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('max_weight_kg', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('pallet_places', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('has_tail_lift', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('has_cooling', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('has_crane', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('adr_approved', sa.Boolean(), server_default=sa.false(), nullable=False))



def downgrade() -> None:
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.drop_column('adr_approved')
        batch_op.drop_column('has_crane')
        batch_op.drop_column('has_cooling')
        batch_op.drop_column('has_tail_lift')
        batch_op.drop_column('pallet_places')
        batch_op.drop_column('max_weight_kg')

    with op.batch_alter_table('drivers', schema=None) as batch_op:
        batch_op.drop_column('has_adr_license')

