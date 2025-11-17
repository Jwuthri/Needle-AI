"""fix_step_status_enum_case

Revision ID: 015
Revises: 014
Create Date: 2025-11-16 21:35:00.000000

This migration fixes the step status enum to use lowercase values
to match the Python enum definition.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add a temporary text column
    op.add_column('chat_message_steps', sa.Column('status_temp', sa.String(50), nullable=True))
    
    # Step 2: Copy and convert uppercase values to lowercase
    op.execute("""
        UPDATE chat_message_steps 
        SET status_temp = CASE 
            WHEN status::text = 'SUCCESS' THEN 'success'
            WHEN status::text = 'ERROR' THEN 'error'
            WHEN status::text = 'PENDING' THEN 'pending'
            ELSE 'success'
        END
    """)
    
    # Step 3: Drop the old status column (this will also drop the constraint)
    op.drop_column('chat_message_steps', 'status')
    
    # Step 4: Drop the old enum type
    op.execute("DROP TYPE IF EXISTS stepstatusenum")
    
    # Step 5: Create new enum type with lowercase values
    new_enum = postgresql.ENUM('success', 'error', 'pending', name='stepstatusenum')
    new_enum.create(op.get_bind(), checkfirst=True)
    
    # Step 6: Rename temp column to status with the new enum type
    op.add_column('chat_message_steps', 
                  sa.Column('status', 
                           sa.Enum('success', 'error', 'pending', name='stepstatusenum'), 
                           nullable=False, 
                           server_default='success'))
    
    # Step 7: Copy data from temp column
    op.execute("""
        UPDATE chat_message_steps 
        SET status = status_temp::stepstatusenum
    """)
    
    # Step 8: Drop the temporary column
    op.drop_column('chat_message_steps', 'status_temp')


def downgrade() -> None:
    # Step 1: Add temporary column
    op.add_column('chat_message_steps', sa.Column('status_temp', sa.String(50), nullable=True))
    
    # Step 2: Copy and convert lowercase to uppercase
    op.execute("""
        UPDATE chat_message_steps 
        SET status_temp = CASE 
            WHEN status::text = 'success' THEN 'SUCCESS'
            WHEN status::text = 'error' THEN 'ERROR'
            WHEN status::text = 'pending' THEN 'PENDING'
            ELSE 'SUCCESS'
        END
    """)
    
    # Step 3: Drop the lowercase status column
    op.drop_column('chat_message_steps', 'status')
    
    # Step 4: Drop the lowercase enum type
    op.execute("DROP TYPE IF EXISTS stepstatusenum")
    
    # Step 5: Create uppercase enum type
    old_enum = postgresql.ENUM('SUCCESS', 'ERROR', 'PENDING', name='stepstatusenum')
    old_enum.create(op.get_bind(), checkfirst=True)
    
    # Step 6: Add status column with uppercase enum
    op.add_column('chat_message_steps',
                  sa.Column('status',
                           sa.Enum('SUCCESS', 'ERROR', 'PENDING', name='stepstatusenum'),
                           nullable=False,
                           server_default='SUCCESS'))
    
    # Step 7: Copy data from temp
    op.execute("""
        UPDATE chat_message_steps 
        SET status = status_temp::stepstatusenum
    """)
    
    # Step 8: Drop temp column
    op.drop_column('chat_message_steps', 'status_temp')

