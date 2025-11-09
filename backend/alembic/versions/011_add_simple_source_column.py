"""Add simple source column and make source_id optional

Revision ID: 011
Revises: 010
Create Date: 2025-11-09 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add simple platform column for storing source platform directly.
    Make source_id optional since we don't always need the complex relationship.
    """
    
    # Add platform column for simple string storage
    op.execute(text('ALTER TABLE reviews ADD COLUMN platform VARCHAR(100)'))
    
    # Make source_id optional (nullable)
    op.execute(text('ALTER TABLE reviews ALTER COLUMN source_id DROP NOT NULL'))
    
    # Create index on platform for filtering
    op.execute(text('CREATE INDEX idx_reviews_platform ON reviews (platform)'))


def downgrade() -> None:
    """Revert changes."""
    
    # Drop index
    op.execute(text('DROP INDEX IF EXISTS idx_reviews_platform'))
    
    # Remove platform column
    op.execute(text('ALTER TABLE reviews DROP COLUMN IF EXISTS platform'))
    
    # Make source_id required again
    op.execute(text('ALTER TABLE reviews ALTER COLUMN source_id SET NOT NULL'))

