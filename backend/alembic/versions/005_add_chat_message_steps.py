"""Add chat message steps table

Revision ID: 005
Revises: 004
Create Date: 2025-01-12

This migration:
- Drops the execution_tree_sessions and execution_tree_nodes tables
- Creates the chat_message_steps table for tracking agent execution steps
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    
    # Drop old execution tree tables if they exist
    op.execute('DROP TABLE IF EXISTS execution_tree_nodes CASCADE')
    op.execute('DROP TABLE IF EXISTS execution_tree_sessions CASCADE')
    
    # Create chat_message_steps table
    op.create_table(
        'chat_message_steps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=False),
        sa.Column('agent_name', sa.String(length=255), nullable=False),
        sa.Column('step_order', sa.Integer(), nullable=False),
        sa.Column('tool_call', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('prediction', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(
        'ix_chat_message_steps_message_id',
        'chat_message_steps',
        ['message_id']
    )
    op.create_index(
        'ix_chat_message_steps_message_order',
        'chat_message_steps',
        ['message_id', 'step_order']
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_chat_message_steps_message_id',
        'chat_message_steps',
        'chat_messages',
        ['message_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade database schema."""
    
    # Drop chat_message_steps table
    op.drop_table('chat_message_steps')
    
    # Recreate execution tree tables (simplified version for rollback)
    op.create_table(
        'execution_tree_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('message_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'execution_tree_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tree_session_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(length=100), nullable=False),
        sa.Column('parent_node_id', sa.String(length=100), nullable=True),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=True),
        sa.Column('tool_name', sa.String(length=255), nullable=True),
        sa.Column('tool_args', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tool_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('input_summary', sa.Text(), nullable=True),
        sa.Column('output_summary', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tree_session_id'], ['execution_tree_sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )

