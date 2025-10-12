"""remove_unused_user_fields

Revision ID: 97d38daa7ebd
Revises: 003
Create Date: 2025-10-11 20:51:15.916800

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop unused columns from users table
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'total_requests')
    op.drop_column('users', 'total_tokens_used')


def downgrade() -> None:
    # Re-add columns if rolling back
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('total_requests', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('total_tokens_used', sa.Integer(), nullable=True, server_default='0'))
