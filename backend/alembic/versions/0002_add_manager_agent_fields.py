"""Add manager agent fields

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add manager agent fields to agents table."""
    # Add manager_type column
    op.add_column('agents', sa.Column('manager_type', sa.String(length=50), nullable=True))
    
    # Add can_generate_tasks column
    op.add_column('agents', sa.Column('can_generate_tasks', sa.Boolean(), nullable=True, default=False))
    
    # Add manager_config column
    op.add_column('agents', sa.Column('manager_config', sa.JSON(), nullable=True))
    
    # Update existing records to have default values
    op.execute("UPDATE agents SET can_generate_tasks = false WHERE can_generate_tasks IS NULL")
    
    # Make can_generate_tasks not nullable with default
    op.alter_column('agents', 'can_generate_tasks', nullable=False, server_default=sa.text('false'))


def downgrade() -> None:
    """Remove manager agent fields from agents table."""
    # Remove manager agent columns
    op.drop_column('agents', 'manager_config')
    op.drop_column('agents', 'can_generate_tasks')
    op.drop_column('agents', 'manager_type') 