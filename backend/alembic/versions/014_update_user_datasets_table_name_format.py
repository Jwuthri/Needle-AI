"""Update user_datasets table_name to user_{id}_table_name format

Revision ID: 014
Revises: 013
Create Date: 2025-01-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def sanitize_table_name(name: str) -> str:
    """Sanitize table name similar to the utility function."""
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    sanitized = sanitized.strip('_')
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    if len(sanitized) > 63:
        sanitized = sanitized[:63]
    return sanitized.lower()


def upgrade() -> None:
    """Update table_name format to user_{id}_table_name."""
    
    # Get connection
    conn = op.get_bind()
    
    # Get all user_datasets records
    result = conn.execute(text("SELECT id, user_id, table_name FROM user_datasets"))
    records = result.fetchall()
    
    for record in records:
        dataset_id, user_id, current_table_name = record
        
        # Skip if already in the new format
        sanitized_user_id = sanitize_table_name(user_id)
        expected_prefix = f"user_{sanitized_user_id}_"
        
        if current_table_name.startswith(expected_prefix):
            continue
        
        # Format new table name
        sanitized_base_name = sanitize_table_name(current_table_name)
        new_table_name = f"user_{sanitized_user_id}_{sanitized_base_name}"
        
        # Update the record
        conn.execute(
            text("UPDATE user_datasets SET table_name = :new_name WHERE id = :id"),
            {"new_name": new_table_name, "id": dataset_id}
        )


def downgrade() -> None:
    """Revert table_name format back to base name only."""
    
    # Get connection
    conn = op.get_bind()
    
    # Get all user_datasets records
    result = conn.execute(text("SELECT id, user_id, table_name FROM user_datasets"))
    records = result.fetchall()
    
    for record in records:
        dataset_id, user_id, current_table_name = record
        
        # Check if in new format
        sanitized_user_id = sanitize_table_name(user_id)
        expected_prefix = f"user_{sanitized_user_id}_"
        
        if not current_table_name.startswith(expected_prefix):
            continue
        
        # Extract base name
        base_name = current_table_name[len(expected_prefix):]
        
        # Update the record
        conn.execute(
            text("UPDATE user_datasets SET table_name = :new_name WHERE id = :id"),
            {"new_name": base_name, "id": dataset_id}
        )

