"""Add thought column to chat_message_steps

Revision ID: 013
Revises: 012
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add thought column to chat_message_steps for reasoning traces."""
    
    # Add thought column to chat_message_steps
    op.add_column(
        'chat_message_steps',
        sa.Column('thought', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    """Remove thought column from chat_message_steps."""
    
    # Drop thought column
    op.drop_column('chat_message_steps', 'thought')
