"""Add review embeddings column

Revision ID: 009
Revises: 008
Create Date: 2025-11-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pgvector extension and embedding column to reviews table."""
    
    # Enable pgvector extension
    op.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    
    # Add embedding column to reviews table
    # OpenAI text-embedding-3-small produces 1536-dimensional vectors
    op.execute(text(
        'ALTER TABLE reviews ADD COLUMN embedding vector(1536)'
    ))
    
    # Create index for vector similarity search (using cosine distance)
    op.execute(text(
        'CREATE INDEX idx_reviews_embedding ON reviews '
        'USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)'
    ))


def downgrade() -> None:
    """Remove embedding column and pgvector extension."""
    
    # Drop index first
    op.execute(text('DROP INDEX IF EXISTS idx_reviews_embedding'))
    
    # Drop embedding column
    op.execute(text('ALTER TABLE reviews DROP COLUMN IF EXISTS embedding'))
    
    # Note: We don't drop the vector extension as other tables might use it
    # If you want to drop it, uncomment the line below:
    # op.execute(text('DROP EXTENSION IF EXISTS vector'))

