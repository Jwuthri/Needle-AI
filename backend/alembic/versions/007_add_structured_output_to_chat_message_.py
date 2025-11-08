"""add_structured_output_to_chat_message_steps

Revision ID: 007
Revises: 006
Create Date: 2025-11-08 12:33:55.283497

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add structured_output column to chat_message_steps
    op.add_column('chat_message_steps', sa.Column('structured_output', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove structured_output column
    op.drop_column('chat_message_steps', 'structured_output')
