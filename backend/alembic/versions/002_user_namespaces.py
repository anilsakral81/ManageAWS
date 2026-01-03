"""Add user_namespaces table for RBAC

Revision ID: 002_user_namespaces
Revises: 001_initial_migration
Create Date: 2026-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_user_namespaces'
down_revision = '001_initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_namespaces table
    op.create_table(
        'user_namespaces',
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('namespace', sa.String(255), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('granted_by', sa.String(255), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('user_id', 'namespace')
    )
    
    # Create indexes
    op.create_index('idx_user_namespace_active', 'user_namespaces', ['user_id', 'namespace', 'enabled'])
    op.create_index(op.f('ix_user_namespaces_user_id'), 'user_namespaces', ['user_id'])
    op.create_index(op.f('ix_user_namespaces_namespace'), 'user_namespaces', ['namespace'])


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_user_namespaces_namespace'), table_name='user_namespaces')
    op.drop_index(op.f('ix_user_namespaces_user_id'), table_name='user_namespaces')
    op.drop_index('idx_user_namespace_active', table_name='user_namespaces')
    
    # Drop table
    op.drop_table('user_namespaces')
