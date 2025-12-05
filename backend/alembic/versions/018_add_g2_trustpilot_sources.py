"""add g2 and trustpilot source types

Revision ID: 018
Revises: 017
Create Date: 2025-01-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add G2 and Trustpilot to SourceTypeEnum."""
    # For PostgreSQL, we need to add new enum values outside of a transaction
    # This is done using raw SQL since Alembic doesn't handle enum alterations well
    
    # Get connection and execute outside transaction
    connection = op.get_bind()
    
    # Check if values already exist before adding
    result = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid "
        "WHERE t.typname = 'sourcetypeenum' AND e.enumlabel = 'g2')"
    ))
    g2_exists = result.scalar()
    
    result = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid "
        "WHERE t.typname = 'sourcetypeenum' AND e.enumlabel = 'trustpilot')"
    ))
    trustpilot_exists = result.scalar()
    
    # Add values if they don't exist
    # Note: These must be run outside transaction, so we commit first
    if not g2_exists:
        connection.execute(sa.text("COMMIT"))
        connection.execute(sa.text("ALTER TYPE sourcetypeenum ADD VALUE 'g2'"))
        
    if not trustpilot_exists:
        connection.execute(sa.text("COMMIT"))
        connection.execute(sa.text("ALTER TYPE sourcetypeenum ADD VALUE 'trustpilot'"))


def downgrade() -> None:
    """Remove G2 and Trustpilot from SourceTypeEnum.
    
    Note: PostgreSQL doesn't support removing enum values directly.
    This would require recreating the enum type and all dependent columns.
    For safety, we'll leave the enum values in place.
    """
    pass

