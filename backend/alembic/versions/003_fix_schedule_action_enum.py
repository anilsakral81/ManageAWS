"""fix schedule action enum values

Revision ID: 003
Revises: 002
Create Date: 2026-01-04 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old enum and recreate with lowercase values
    # First, alter the column to use a temporary type
    op.execute("ALTER TABLE schedules ALTER COLUMN action TYPE VARCHAR USING action::text")
    
    # Drop the old enum type
    op.execute("DROP TYPE IF EXISTS scheduleaction")
    
    # Create the new enum type with lowercase values
    op.execute("CREATE TYPE scheduleaction AS ENUM ('start', 'stop')")
    
    # Update any existing uppercase values to lowercase
    op.execute("UPDATE schedules SET action = LOWER(action)")
    
    # Convert the column back to the enum type
    op.execute("ALTER TABLE schedules ALTER COLUMN action TYPE scheduleaction USING action::scheduleaction")


def downgrade() -> None:
    # Revert to uppercase enum values
    op.execute("ALTER TABLE schedules ALTER COLUMN action TYPE VARCHAR USING action::text")
    op.execute("DROP TYPE IF EXISTS scheduleaction")
    op.execute("CREATE TYPE scheduleaction AS ENUM ('START', 'STOP')")
    op.execute("UPDATE schedules SET action = UPPER(action)")
    op.execute("ALTER TABLE schedules ALTER COLUMN action TYPE scheduleaction USING action::scheduleaction")
