"""add_eda_fields_to_user_datasets

Revision ID: 013
Revises: 012
Create Date: 2025-11-13 20:05:47.964880

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new EDA fields to user_datasets table
    op.add_column('user_datasets', sa.Column('field_metadata', sa.JSON(), nullable=True))
    op.add_column('user_datasets', sa.Column('column_stats', sa.JSON(), nullable=True))
    op.add_column('user_datasets', sa.Column('sample_data', sa.JSON(), nullable=True))
    op.add_column('user_datasets', sa.Column('vector_store_columns', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove EDA fields from user_datasets table
    op.drop_column('user_datasets', 'vector_store_columns')
    op.drop_column('user_datasets', 'sample_data')
    op.drop_column('user_datasets', 'column_stats')
    op.drop_column('user_datasets', 'field_metadata')
