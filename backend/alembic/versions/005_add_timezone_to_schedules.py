"""Add timezone column to schedules

Revision ID: 005
Revises: 004
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add timezone column to schedules table"""
    # Add timezone column with default 'UTC'
    op.add_column('schedules', 
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC')
    )
    
    # Remove server_default after adding (we want default in code, not DB)
    op.alter_column('schedules', 'timezone', server_default=None)


def downgrade() -> None:
    """Remove timezone column from schedules table"""
    op.drop_column('schedules', 'timezone')
