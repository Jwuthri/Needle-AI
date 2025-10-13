"""add_cascade_deletes

Revision ID: 8c18c2291307
Revises: 005
Create Date: 2025-10-12 16:34:43.083555

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c18c2291307'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add CASCADE delete to all foreign key relationships."""
    
    # ChatSession -> User (CASCADE)
    op.drop_constraint('chat_sessions_user_id_fkey', 'chat_sessions', type_='foreignkey')
    op.create_foreign_key('chat_sessions_user_id_fkey', 'chat_sessions', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # ChatMessage -> ChatSession (CASCADE)
    op.drop_constraint('chat_messages_session_id_fkey', 'chat_messages', type_='foreignkey')
    op.create_foreign_key('chat_messages_session_id_fkey', 'chat_messages', 'chat_sessions', ['session_id'], ['id'], ondelete='CASCADE')
    
    # ChatMessage -> ChatMessage (self-referential CASCADE)
    op.drop_constraint('chat_messages_parent_message_id_fkey', 'chat_messages', type_='foreignkey')
    op.create_foreign_key('chat_messages_parent_message_id_fkey', 'chat_messages', 'chat_messages', ['parent_message_id'], ['id'], ondelete='CASCADE')
    
    # Company -> User (CASCADE)
    op.drop_constraint('companies_created_by_fkey', 'companies', type_='foreignkey')
    op.create_foreign_key('companies_created_by_fkey', 'companies', 'users', ['created_by'], ['id'], ondelete='CASCADE')
    
    # Review -> Company (CASCADE)
    op.drop_constraint('reviews_company_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_company_id_fkey', 'reviews', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
    
    # Review -> ReviewSource (CASCADE)
    op.drop_constraint('reviews_source_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_source_id_fkey', 'reviews', 'review_sources', ['source_id'], ['id'], ondelete='CASCADE')
    
    # Review -> ScrapingJob (CASCADE)
    op.drop_constraint('reviews_scraping_job_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_scraping_job_id_fkey', 'reviews', 'scraping_jobs', ['scraping_job_id'], ['id'], ondelete='CASCADE')
    
    # ScrapingJob -> Company (CASCADE)
    op.drop_constraint('scraping_jobs_company_id_fkey', 'scraping_jobs', type_='foreignkey')
    op.create_foreign_key('scraping_jobs_company_id_fkey', 'scraping_jobs', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
    
    # ScrapingJob -> ReviewSource (CASCADE)
    op.drop_constraint('scraping_jobs_source_id_fkey', 'scraping_jobs', type_='foreignkey')
    op.create_foreign_key('scraping_jobs_source_id_fkey', 'scraping_jobs', 'review_sources', ['source_id'], ['id'], ondelete='CASCADE')
    
    # ScrapingJob -> User (CASCADE)
    op.drop_constraint('scraping_jobs_user_id_fkey', 'scraping_jobs', type_='foreignkey')
    op.create_foreign_key('scraping_jobs_user_id_fkey', 'scraping_jobs', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # DataImport -> Company (CASCADE)
    op.drop_constraint('data_imports_company_id_fkey', 'data_imports', type_='foreignkey')
    op.create_foreign_key('data_imports_company_id_fkey', 'data_imports', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
    
    # DataImport -> User (CASCADE)
    op.drop_constraint('data_imports_user_id_fkey', 'data_imports', type_='foreignkey')
    op.create_foreign_key('data_imports_user_id_fkey', 'data_imports', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # UserCredit -> User (CASCADE)
    op.drop_constraint('user_credits_user_id_fkey', 'user_credits', type_='foreignkey')
    op.create_foreign_key('user_credits_user_id_fkey', 'user_credits', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # CreditTransaction -> UserCredit (CASCADE)
    op.drop_constraint('credit_transactions_user_credit_id_fkey', 'credit_transactions', type_='foreignkey')
    op.create_foreign_key('credit_transactions_user_credit_id_fkey', 'credit_transactions', 'user_credits', ['user_credit_id'], ['id'], ondelete='CASCADE')
    
    # CreditTransaction -> ScrapingJob (SET NULL)
    op.drop_constraint('credit_transactions_scraping_job_id_fkey', 'credit_transactions', type_='foreignkey')
    op.create_foreign_key('credit_transactions_scraping_job_id_fkey', 'credit_transactions', 'scraping_jobs', ['scraping_job_id'], ['id'], ondelete='SET NULL')
    
    # ApiKey -> User (CASCADE)
    op.drop_constraint('api_keys_user_id_fkey', 'api_keys', type_='foreignkey')
    op.create_foreign_key('api_keys_user_id_fkey', 'api_keys', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    # TaskResult -> User (SET NULL)
    op.drop_constraint('task_results_user_id_fkey', 'task_results', type_='foreignkey')
    op.create_foreign_key('task_results_user_id_fkey', 'task_results', 'users', ['user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Remove CASCADE delete from foreign key relationships."""
    
    # Restore original foreign keys without CASCADE
    
    # TaskResult -> User
    op.drop_constraint('task_results_user_id_fkey', 'task_results', type_='foreignkey')
    op.create_foreign_key('task_results_user_id_fkey', 'task_results', 'users', ['user_id'], ['id'])
    
    # ApiKey -> User
    op.drop_constraint('api_keys_user_id_fkey', 'api_keys', type_='foreignkey')
    op.create_foreign_key('api_keys_user_id_fkey', 'api_keys', 'users', ['user_id'], ['id'])
    
    # CreditTransaction -> ScrapingJob
    op.drop_constraint('credit_transactions_scraping_job_id_fkey', 'credit_transactions', type_='foreignkey')
    op.create_foreign_key('credit_transactions_scraping_job_id_fkey', 'credit_transactions', 'scraping_jobs', ['scraping_job_id'], ['id'])
    
    # CreditTransaction -> UserCredit
    op.drop_constraint('credit_transactions_user_credit_id_fkey', 'credit_transactions', type_='foreignkey')
    op.create_foreign_key('credit_transactions_user_credit_id_fkey', 'credit_transactions', 'user_credits', ['user_credit_id'], ['id'])
    
    # UserCredit -> User
    op.drop_constraint('user_credits_user_id_fkey', 'user_credits', type_='foreignkey')
    op.create_foreign_key('user_credits_user_id_fkey', 'user_credits', 'users', ['user_id'], ['id'])
    
    # DataImport -> User
    op.drop_constraint('data_imports_user_id_fkey', 'data_imports', type_='foreignkey')
    op.create_foreign_key('data_imports_user_id_fkey', 'data_imports', 'users', ['user_id'], ['id'])
    
    # DataImport -> Company
    op.drop_constraint('data_imports_company_id_fkey', 'data_imports', type_='foreignkey')
    op.create_foreign_key('data_imports_company_id_fkey', 'data_imports', 'companies', ['company_id'], ['id'])
    
    # ScrapingJob -> User
    op.drop_constraint('scraping_jobs_user_id_fkey', 'scraping_jobs', type_='foreignkey')
    op.create_foreign_key('scraping_jobs_user_id_fkey', 'scraping_jobs', 'users', ['user_id'], ['id'])
    
    # ScrapingJob -> ReviewSource
    op.drop_constraint('scraping_jobs_source_id_fkey', 'scraping_jobs', type_='foreignkey')
    op.create_foreign_key('scraping_jobs_source_id_fkey', 'scraping_jobs', 'review_sources', ['source_id'], ['id'])
    
    # ScrapingJob -> Company
    op.drop_constraint('scraping_jobs_company_id_fkey', 'scraping_jobs', type_='foreignkey')
    op.create_foreign_key('scraping_jobs_company_id_fkey', 'scraping_jobs', 'companies', ['company_id'], ['id'])
    
    # Review -> ScrapingJob
    op.drop_constraint('reviews_scraping_job_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_scraping_job_id_fkey', 'reviews', 'scraping_jobs', ['scraping_job_id'], ['id'])
    
    # Review -> ReviewSource
    op.drop_constraint('reviews_source_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_source_id_fkey', 'reviews', 'review_sources', ['source_id'], ['id'])
    
    # Review -> Company
    op.drop_constraint('reviews_company_id_fkey', 'reviews', type_='foreignkey')
    op.create_foreign_key('reviews_company_id_fkey', 'reviews', 'companies', ['company_id'], ['id'])
    
    # Company -> User
    op.drop_constraint('companies_created_by_fkey', 'companies', type_='foreignkey')
    op.create_foreign_key('companies_created_by_fkey', 'companies', 'users', ['created_by'], ['id'])
    
    # ChatMessage -> ChatMessage
    op.drop_constraint('chat_messages_parent_message_id_fkey', 'chat_messages', type_='foreignkey')
    op.create_foreign_key('chat_messages_parent_message_id_fkey', 'chat_messages', 'chat_messages', ['parent_message_id'], ['id'])
    
    # ChatMessage -> ChatSession
    op.drop_constraint('chat_messages_session_id_fkey', 'chat_messages', type_='foreignkey')
    op.create_foreign_key('chat_messages_session_id_fkey', 'chat_messages', 'chat_sessions', ['session_id'], ['id'])
    
    # ChatSession -> User
    op.drop_constraint('chat_sessions_user_id_fkey', 'chat_sessions', type_='foreignkey')
    op.create_foreign_key('chat_sessions_user_id_fkey', 'chat_sessions', 'users', ['user_id'], ['id'])
