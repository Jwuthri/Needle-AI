"""Remove redundant vector_id column

Revision ID: 010
Revises: 009
Create Date: 2025-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove vector_id column - just use review.id for external vector stores."""
    
    # Drop index first
    op.execute(text('DROP INDEX IF EXISTS idx_reviews_vector'))
    
    # Drop the column
    op.execute(text('ALTER TABLE reviews DROP COLUMN IF EXISTS vector_id'))


def downgrade() -> None:
    """Re-add vector_id column if needed."""
    
    # Add column back
    op.execute(text('ALTER TABLE reviews ADD COLUMN vector_id VARCHAR'))
    
    # Recreate index
    op.execute(text('CREATE INDEX idx_reviews_vector ON reviews (vector_id)'))

