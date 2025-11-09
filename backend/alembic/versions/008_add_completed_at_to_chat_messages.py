"""add completed_at to chat_messages

Revision ID: 008_add_completed_at
Revises: 007_add_structured_output_to_chat_message_
Create Date: 2025-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add completed_at column to chat_messages table."""
    # Add completed_at column
    op.add_column('chat_messages', sa.Column('completed_at', sa.DateTime(), nullable=True))
    
    # Create index for completed_at (useful for analytics)
    op.create_index('ix_chat_message_completed_at', 'chat_messages', ['completed_at'])


def downgrade() -> None:
    """Remove completed_at column from chat_messages table."""
    # Drop index
    op.drop_index('ix_chat_message_completed_at', table_name='chat_messages')
    
    # Drop column
    op.drop_column('chat_messages', 'completed_at')

