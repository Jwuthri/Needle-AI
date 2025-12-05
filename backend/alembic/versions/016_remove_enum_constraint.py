"""remove_enum_constraint

Revision ID: 016
Revises: 015
Create Date: 2025-11-16 21:55:00.000000

Remove the enum constraint and use a simple string column instead.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Change status column to VARCHAR without enum constraint
    op.execute("""
        ALTER TABLE chat_message_steps 
        ALTER COLUMN status TYPE VARCHAR(50)
    """)
    
    # Step 2: Drop the enum type
    op.execute("DROP TYPE IF EXISTS stepstatusenum CASCADE")


def downgrade() -> None:
    # Recreate enum type
    op.execute("CREATE TYPE stepstatusenum AS ENUM ('success', 'error', 'pending')")
    
    # Convert column back to enum
    op.execute("""
        ALTER TABLE chat_message_steps 
        ALTER COLUMN status TYPE stepstatusenum USING status::stepstatusenum
    """)

