"""Product Review Platform Migration

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to product review platform schema."""
    
    # Drop completions table (no longer needed)
    op.execute(text('DROP TABLE IF EXISTS completions CASCADE'))
    
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_companies_user_created', 'companies', ['created_by', 'created_at'])
    op.create_index('idx_companies_domain', 'companies', ['domain'])
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'])
    
    # Create review_sources table
    op.create_table(
        'review_sources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.Enum('REDDIT', 'TWITTER', 'CUSTOM_CSV', 'CUSTOM_JSON', name='sourcetypeenum'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('cost_per_review', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_sources_type_active', 'review_sources', ['source_type', 'is_active'])
    op.create_index(op.f('ix_review_sources_name'), 'review_sources', ['name'])
    op.create_index(op.f('ix_review_sources_source_type'), 'review_sources', ['source_type'])
    
    # Create user_credits table
    op.create_table(
        'user_credits',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('credits_available', sa.Float(), nullable=False),
        sa.Column('total_purchased', sa.Float(), nullable=False),
        sa.Column('total_spent', sa.Float(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_purchase_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('stripe_customer_id')
    )
    op.create_index('idx_user_credits_stripe', 'user_credits', ['stripe_customer_id'])
    op.create_index(op.f('ix_user_credits_user_id'), 'user_credits', ['user_id'])
    
    # Create scraping_jobs table
    op.create_table(
        'scraping_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='jobstatusenum'), nullable=False),
        sa.Column('progress_percentage', sa.Float(), nullable=False),
        sa.Column('total_reviews_target', sa.Integer(), nullable=False),
        sa.Column('reviews_fetched', sa.Integer(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=False),
        sa.Column('celery_task_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['source_id'], ['review_sources.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_jobs_status_created', 'scraping_jobs', ['status', 'created_at'])
    op.create_index('idx_jobs_user_created', 'scraping_jobs', ['user_id', 'created_at'])
    op.create_index('idx_jobs_company', 'scraping_jobs', ['company_id', 'created_at'])
    op.create_index('idx_jobs_celery_task', 'scraping_jobs', ['celery_task_id'])
    op.create_index(op.f('ix_scraping_jobs_status'), 'scraping_jobs', ['status'])
    op.create_index(op.f('ix_scraping_jobs_celery_task_id'), 'scraping_jobs', ['celery_task_id'])
    
    # Create data_imports table
    op.create_table(
        'data_imports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('import_type', sa.Enum('CSV', 'JSON', 'XLSX', name='importtypeenum'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='importstatusenum'), nullable=False),
        sa.Column('rows_imported', sa.Integer(), nullable=False),
        sa.Column('rows_failed', sa.Integer(), nullable=False),
        sa.Column('celery_task_id', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_imports_status_created', 'data_imports', ['status', 'created_at'])
    op.create_index('idx_imports_user_created', 'data_imports', ['user_id', 'created_at'])
    op.create_index('idx_imports_company', 'data_imports', ['company_id', 'created_at'])
    op.create_index('idx_imports_celery_task', 'data_imports', ['celery_task_id'])
    op.create_index(op.f('ix_data_imports_status'), 'data_imports', ['status'])
    op.create_index(op.f('ix_data_imports_celery_task_id'), 'data_imports', ['celery_task_id'])
    
    # Create reviews table
    op.create_table(
        'reviews',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('company_id', sa.String(), nullable=False),
        sa.Column('source_id', sa.String(), nullable=False),
        sa.Column('scraping_job_id', sa.String(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('author', sa.String(length=255), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=False),
        sa.Column('vector_id', sa.String(), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['scraping_job_id'], ['scraping_jobs.id'], ),
        sa.ForeignKeyConstraint(['source_id'], ['review_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reviews_company_scraped', 'reviews', ['company_id', 'scraped_at'])
    op.create_index('idx_reviews_sentiment', 'reviews', ['sentiment_score'])
    op.create_index('idx_reviews_source', 'reviews', ['source_id', 'scraped_at'])
    op.create_index('idx_reviews_job', 'reviews', ['scraping_job_id'])
    op.create_index('idx_reviews_vector', 'reviews', ['vector_id'])
    op.create_index(op.f('ix_reviews_vector_id'), 'reviews', ['vector_id'])
    
    # Create credit_transactions table
    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_credit_id', sa.String(), nullable=False),
        sa.Column('scraping_job_id', sa.String(), nullable=True),
        sa.Column('transaction_type', sa.Enum('PURCHASE', 'DEDUCTION', 'REFUND', 'BONUS', name='transactiontypeenum'), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
        sa.Column('balance_before', sa.Float(), nullable=False),
        sa.Column('balance_after', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_credit_id'], ['user_credits.id'], ),
        sa.ForeignKeyConstraint(['scraping_job_id'], ['scraping_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_transactions_user_created', 'credit_transactions', ['user_credit_id', 'created_at'])
    op.create_index('idx_transactions_type', 'credit_transactions', ['transaction_type', 'created_at'])
    op.create_index('idx_transactions_stripe', 'credit_transactions', ['stripe_payment_intent_id'])
    op.create_index(op.f('ix_credit_transactions_transaction_type'), 'credit_transactions', ['transaction_type'])
    op.create_index(op.f('ix_credit_transactions_stripe_payment_intent_id'), 'credit_transactions', ['stripe_payment_intent_id'])
    op.create_index(op.f('ix_credit_transactions_created_at'), 'credit_transactions', ['created_at'])
    
    # Seed default review sources
    op.execute(text("""
        INSERT INTO review_sources (id, name, source_type, description, config, cost_per_review, is_active, created_at, updated_at)
        VALUES 
            (gen_random_uuid()::text, 'Reddit', 'REDDIT', 'Reddit forum discussions and comments', '{}', 0.01, true, NOW(), NOW()),
            (gen_random_uuid()::text, 'Twitter/X', 'TWITTER', 'Twitter posts and discussions', '{}', 0.01, true, NOW(), NOW()),
            (gen_random_uuid()::text, 'CSV Import', 'CUSTOM_CSV', 'User-uploaded CSV files', '{}', 0.0, true, NOW(), NOW())
    """))


def downgrade() -> None:
    """Downgrade from product review platform schema."""
    
    # Drop all new tables in reverse order
    op.drop_table('credit_transactions')
    op.drop_table('reviews')
    op.drop_table('data_imports')
    op.drop_table('scraping_jobs')
    op.drop_table('user_credits')
    op.drop_table('review_sources')
    op.drop_table('companies')
    
    # Drop enums
    op.execute(text('DROP TYPE IF EXISTS transactiontypeenum'))
    op.execute(text('DROP TYPE IF EXISTS importstatusenum'))
    op.execute(text('DROP TYPE IF EXISTS importtypeenum'))
    op.execute(text('DROP TYPE IF EXISTS jobstatusenum'))
    op.execute(text('DROP TYPE IF EXISTS sourcetypeenum'))
    
    # Recreate completions table (optional, for rollback support)
    # You may want to add this if you need to rollback cleanly

