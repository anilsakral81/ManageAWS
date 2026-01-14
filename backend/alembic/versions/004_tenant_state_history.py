"""Add tenant state history table

Revision ID: 004
Revises: 003
Create Date: 2026-01-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenant_state_history table
    op.create_table(
        'tenant_state_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('previous_state', sa.Enum('running', 'stopped', 'scaling', 'unknown', name='statetype'), nullable=True),
        sa.Column('new_state', sa.Enum('running', 'stopped', 'scaling', 'unknown', name='statetype'), nullable=False),
        sa.Column('previous_replicas', sa.Integer(), nullable=True),
        sa.Column('new_replicas', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('changed_by', sa.String(length=255), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_tenant_state_history_id'), 'tenant_state_history', ['id'], unique=False)
    op.create_index(op.f('ix_tenant_state_history_tenant_id'), 'tenant_state_history', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_tenant_state_history_new_state'), 'tenant_state_history', ['new_state'], unique=False)
    op.create_index(op.f('ix_tenant_state_history_changed_at'), 'tenant_state_history', ['changed_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tenant_state_history_changed_at'), table_name='tenant_state_history')
    op.drop_index(op.f('ix_tenant_state_history_new_state'), table_name='tenant_state_history')
    op.drop_index(op.f('ix_tenant_state_history_tenant_id'), table_name='tenant_state_history')
    op.drop_index(op.f('ix_tenant_state_history_id'), table_name='tenant_state_history')
    op.drop_table('tenant_state_history')
    
    # Drop enum
    sa.Enum(name='statetype').drop(op.get_bind(), checkfirst=True)
