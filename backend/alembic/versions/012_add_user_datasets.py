"""Add user_datasets table

Revision ID: 012
Revises: 011
Create Date: 2024-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user_datasets table for CSV uploads."""
    
    # Create user_datasets table
    op.create_table(
        'user_datasets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('origin', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(length=255), nullable=False),
        sa.Column('meta', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_user_datasets_user_created', 'user_datasets', ['user_id', 'created_at'])
    op.create_index('idx_user_datasets_table_name', 'user_datasets', ['table_name'])
    op.create_index('idx_user_datasets_user_table', 'user_datasets', ['user_id', 'table_name'])


def downgrade() -> None:
    """Remove user_datasets table."""
    
    # Drop indexes
    op.drop_index('idx_user_datasets_user_table', table_name='user_datasets')
    op.drop_index('idx_user_datasets_table_name', table_name='user_datasets')
    op.drop_index('idx_user_datasets_user_created', table_name='user_datasets')
    
    # Drop table
    op.drop_table('user_datasets')

