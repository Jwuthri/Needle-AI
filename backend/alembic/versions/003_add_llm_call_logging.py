"""add llm call logging table

Revision ID: 003_add_llm_call_logging
Revises: 002_product_review_platform
Create Date: 2025-01-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_llm_call_logging'
down_revision = '002_product_review_platform'
branch_labels = None
depends_on = None


def upgrade():
    # Create llm_calls table
    op.create_table(
        'llm_calls',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('call_type', sa.Enum('CHAT', 'RAG_QUERY', 'RAG_SYNTHESIS', 'SENTIMENT_ANALYSIS', 'SUMMARIZATION', 'EMBEDDING', 'CLASSIFICATION', 'EXTRACTION', 'SYSTEM', 'OTHER', name='llmcalltypeenum'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'SUCCESS', 'ERROR', 'TIMEOUT', 'RATE_LIMITED', name='llmcallstatusenum'), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('messages', sa.JSON(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('tools', sa.JSON(), nullable=True),
        sa.Column('tool_choice', sa.String(length=50), nullable=True),
        sa.Column('request_params', sa.JSON(), nullable=True),
        sa.Column('response_message', sa.JSON(), nullable=True),
        sa.Column('finish_reason', sa.String(length=50), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('task_id', sa.String(), nullable=True),
        sa.Column('company_id', sa.String(), nullable=True),
        sa.Column('review_id', sa.String(), nullable=True),
        sa.Column('trace_id', sa.String(), nullable=True),
        sa.Column('parent_call_id', sa.String(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('idx_llm_call_type_status', 'llm_calls', ['call_type', 'status'])
    op.create_index('idx_llm_call_provider_model', 'llm_calls', ['provider', 'model'])
    op.create_index('idx_llm_call_user_created', 'llm_calls', ['user_id', 'created_at'])
    op.create_index('idx_llm_call_created_at', 'llm_calls', ['created_at'])
    op.create_index('idx_llm_call_trace', 'llm_calls', ['trace_id'])
    op.create_index(op.f('ix_llm_calls_user_id'), 'llm_calls', ['user_id'], unique=False)
    op.create_index(op.f('ix_llm_calls_session_id'), 'llm_calls', ['session_id'], unique=False)
    op.create_index(op.f('ix_llm_calls_task_id'), 'llm_calls', ['task_id'], unique=False)
    op.create_index(op.f('ix_llm_calls_company_id'), 'llm_calls', ['company_id'], unique=False)
    op.create_index(op.f('ix_llm_calls_review_id'), 'llm_calls', ['review_id'], unique=False)
    op.create_index(op.f('ix_llm_calls_parent_call_id'), 'llm_calls', ['parent_call_id'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_llm_calls_parent_call_id'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_review_id'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_company_id'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_task_id'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_session_id'), table_name='llm_calls')
    op.drop_index(op.f('ix_llm_calls_user_id'), table_name='llm_calls')
    op.drop_index('idx_llm_call_trace', table_name='llm_calls')
    op.drop_index('idx_llm_call_created_at', table_name='llm_calls')
    op.drop_index('idx_llm_call_user_created', table_name='llm_calls')
    op.drop_index('idx_llm_call_provider_model', table_name='llm_calls')
    op.drop_index('idx_llm_call_type_status', table_name='llm_calls')
    
    # Drop table
    op.drop_table('llm_calls')
    
    # Drop enums (PostgreSQL only)
    # Note: This might fail on other databases, but that's okay
    try:
        op.execute('DROP TYPE llmcallstatusenum')
        op.execute('DROP TYPE llmcalltypeenum')
    except:
        pass

