"""convert enum to string

Revision ID: 019
Revises: 018
Create Date: 2025-01-19 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert source_type from enum to string."""
    
    # Step 1: Add new string column
    op.add_column('review_sources', sa.Column('source_type_str', sa.String(50), nullable=True))
    
    # Step 2: Copy data from enum to string
    op.execute("""
        UPDATE review_sources 
        SET source_type_str = LOWER(source_type::text)
    """)
    
    # Step 3: Drop the old enum column
    op.drop_index('ix_review_sources_source_type', table_name='review_sources')
    op.drop_index('idx_sources_type_active', table_name='review_sources')
    op.drop_column('review_sources', 'source_type')
    
    # Step 4: Rename new column to source_type
    op.alter_column('review_sources', 'source_type_str', new_column_name='source_type', nullable=False)
    
    # Step 5: Recreate indexes
    op.create_index('ix_review_sources_source_type', 'review_sources', ['source_type'])
    op.create_index('idx_sources_type_active', 'review_sources', ['source_type', 'is_active'])
    
    # Step 6: Drop the enum type
    op.execute('DROP TYPE IF EXISTS sourcetypeenum CASCADE')


def downgrade() -> None:
    """Convert source_type from string back to enum."""
    
    # Recreate enum type
    op.execute("""
        CREATE TYPE sourcetypeenum AS ENUM ('reddit', 'twitter', 'g2', 'trustpilot', 'custom_csv', 'custom_json')
    """)
    
    # Add new enum column
    op.add_column('review_sources', sa.Column('source_type_enum', sa.Enum('reddit', 'twitter', 'g2', 'trustpilot', 'custom_csv', 'custom_json', name='sourcetypeenum'), nullable=True))
    
    # Copy data with uppercase conversion
    op.execute("""
        UPDATE review_sources 
        SET source_type_enum = UPPER(source_type)::sourcetypeenum
    """)
    
    # Drop old column and indexes
    op.drop_index('ix_review_sources_source_type', table_name='review_sources')
    op.drop_index('idx_sources_type_active', table_name='review_sources')
    op.drop_column('review_sources', 'source_type')
    
    # Rename enum column
    op.alter_column('review_sources', 'source_type_enum', new_column_name='source_type', nullable=False)
    
    # Recreate indexes
    op.create_index('ix_review_sources_source_type', 'review_sources', ['source_type'])
    op.create_index('idx_sources_type_active', 'review_sources', ['source_type', 'is_active'])

