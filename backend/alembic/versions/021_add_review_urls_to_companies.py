"""Add review_urls JSON column to companies table.

Revision ID: 021
Revises: 020
Create Date: 2024-11-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("review_urls", sa.JSON(), nullable=True, default={})
    )


def downgrade() -> None:
    op.drop_column("companies", "review_urls")

