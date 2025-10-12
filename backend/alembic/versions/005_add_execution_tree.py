"""add execution tree tables

Revision ID: 005
Revises: 004
Create Date: 2025-10-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums manually to avoid duplicate errors
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'executionnodetype') THEN CREATE TYPE executionnodetype AS ENUM ('query', 'tool', 'agent', 'llm_call', 'subtask'); END IF; END $$;")
    op.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'executionnodestatus') THEN CREATE TYPE executionnodestatus AS ENUM ('pending', 'running', 'completed', 'failed'); END IF; END $$;")
    
    # Create execution_tree_sessions table
    op.create_table(
        'execution_tree_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('message_id', sa.String(length=255), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='executionnodestatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('result_summary', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_tree_sessions_id'), 'execution_tree_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_execution_tree_sessions_session_id'), 'execution_tree_sessions', ['session_id'], unique=False)
    op.create_index(op.f('ix_execution_tree_sessions_message_id'), 'execution_tree_sessions', ['message_id'], unique=False)
    op.create_index(op.f('ix_execution_tree_sessions_user_id'), 'execution_tree_sessions', ['user_id'], unique=False)
    
    # Create execution_tree_nodes table
    op.create_table(
        'execution_tree_nodes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tree_session_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(length=100), nullable=False),
        sa.Column('parent_node_id', sa.String(length=100), nullable=True),
        sa.Column('node_type', sa.Enum('query', 'tool', 'agent', 'llm_call', 'subtask', name='executionnodetype'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='executionnodestatus'), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=True),
        sa.Column('tool_name', sa.String(length=255), nullable=True),
        sa.Column('tool_args', sa.JSON(), nullable=True),
        sa.Column('tool_result', sa.JSON(), nullable=True),
        sa.Column('input_summary', sa.Text(), nullable=True),
        sa.Column('output_summary', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tree_session_id'], ['execution_tree_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_tree_nodes_id'), 'execution_tree_nodes', ['id'], unique=False)
    op.create_index(op.f('ix_execution_tree_nodes_tree_session_id'), 'execution_tree_nodes', ['tree_session_id'], unique=False)
    op.create_index(op.f('ix_execution_tree_nodes_node_id'), 'execution_tree_nodes', ['node_id'], unique=False)
    op.create_index(op.f('ix_execution_tree_nodes_parent_node_id'), 'execution_tree_nodes', ['parent_node_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_execution_tree_nodes_parent_node_id'), table_name='execution_tree_nodes')
    op.drop_index(op.f('ix_execution_tree_nodes_node_id'), table_name='execution_tree_nodes')
    op.drop_index(op.f('ix_execution_tree_nodes_tree_session_id'), table_name='execution_tree_nodes')
    op.drop_index(op.f('ix_execution_tree_nodes_id'), table_name='execution_tree_nodes')
    op.drop_table('execution_tree_nodes')
    
    op.drop_index(op.f('ix_execution_tree_sessions_user_id'), table_name='execution_tree_sessions')
    op.drop_index(op.f('ix_execution_tree_sessions_message_id'), table_name='execution_tree_sessions')
    op.drop_index(op.f('ix_execution_tree_sessions_session_id'), table_name='execution_tree_sessions')
    op.drop_index(op.f('ix_execution_tree_sessions_id'), table_name='execution_tree_sessions')
    op.drop_table('execution_tree_sessions')
    
    # Drop enums
    sa.Enum(name='executionnodestatus').drop(op.get_bind())
    sa.Enum(name='executionnodetype').drop(op.get_bind())

