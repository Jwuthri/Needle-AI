"""add_status_to_chat_message_steps

Revision ID: 014
Revises: 013
Create Date: 2025-11-16 21:07:56.426369

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old enum if it exists (in case migration was partially run with uppercase values)
    op.execute("DROP TYPE IF EXISTS stepstatusenum CASCADE")
    
    # Create enum type with lowercase values (to match Python enum)
    step_status_enum = postgresql.ENUM('success', 'error', 'pending', name='stepstatusenum')
    step_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Add status column to chat_message_steps with default value
    op.add_column('chat_message_steps', sa.Column('status', sa.Enum('success', 'error', 'pending', name='stepstatusenum'), nullable=False, server_default='success'))


def downgrade() -> None:
    # Drop status column from chat_message_steps
    op.drop_column('chat_message_steps', 'status')
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS stepstatusenum")
