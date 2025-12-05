"""add_raw_output_to_chat_message_steps

Revision ID: 017
Revises: 016
Create Date: 2025-11-17 00:00:00.000000

This migration adds a raw_output column to store the raw unprocessed output
from agents, separate from the structured_output field.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add raw_output column to store raw agent output
    op.add_column('chat_message_steps', 
                  sa.Column('raw_output', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove raw_output column
    op.drop_column('chat_message_steps', 'raw_output')

