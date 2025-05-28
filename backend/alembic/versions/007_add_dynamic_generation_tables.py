"""Add dynamic crew generation tables

Revision ID: 007
Revises: 006
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    """Add dynamic crew generation tables."""
    
    # Create dynamic_crew_templates table
    op.create_table(
        'dynamic_crew_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', sa.String(length=100), nullable=False),
        sa.Column('template_config', sa.JSON(), nullable=False),
        sa.Column('success_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_dynamic_crew_templates_name', 'name'),
        sa.Index('ix_dynamic_crew_templates_template_type', 'template_type'),
        sa.Index('ix_dynamic_crew_templates_is_active', 'is_active')
    )
    
    # Create generation_requests table
    op.create_table(
        'generation_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('requirements', sa.JSON(), nullable=True),
        sa.Column('generated_crew_id', sa.Integer(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('llm_provider', sa.String(length=100), nullable=False, default='openai'),
        sa.Column('generation_status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('generation_result', sa.JSON(), nullable=True),
        sa.Column('validation_result', sa.JSON(), nullable=True),
        sa.Column('optimization_applied', sa.Boolean(), nullable=False, default=False),
        sa.Column('generation_time_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['generated_crew_id'], ['crews.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['dynamic_crew_templates.id'], ondelete='SET NULL'),
        sa.Index('ix_generation_requests_status', 'generation_status'),
        sa.Index('ix_generation_requests_created_at', 'created_at'),
        sa.Index('ix_generation_requests_template_id', 'template_id')
    )
    
    # Create crew_optimizations table
    op.create_table(
        'crew_optimizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('optimization_type', sa.String(length=100), nullable=False),
        sa.Column('original_config', sa.JSON(), nullable=False),
        sa.Column('optimized_config', sa.JSON(), nullable=True),
        sa.Column('optimization_score', sa.Float(), nullable=True),
        sa.Column('optimization_metrics', sa.JSON(), nullable=True),
        sa.Column('applied', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ondelete='CASCADE'),
        sa.Index('ix_crew_optimizations_crew_id', 'crew_id'),
        sa.Index('ix_crew_optimizations_type', 'optimization_type'),
        sa.Index('ix_crew_optimizations_applied', 'applied')
    )
    
    # Create agent_capabilities table
    op.create_table(
        'agent_capabilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('capability_name', sa.String(length=255), nullable=False),
        sa.Column('capability_type', sa.String(length=100), nullable=False),
        sa.Column('proficiency_level', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.Index('ix_agent_capabilities_agent_id', 'agent_id'),
        sa.Index('ix_agent_capabilities_name', 'capability_name'),
        sa.Index('ix_agent_capabilities_type', 'capability_type')
    )
    
    # Create task_requirements table
    op.create_table(
        'task_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('generation_request_id', sa.Integer(), nullable=True),
        sa.Column('requirement_type', sa.String(length=100), nullable=False),
        sa.Column('requirement_name', sa.String(length=255), nullable=False),
        sa.Column('requirement_value', sa.Text(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=3),
        sa.Column('satisfied', sa.Boolean(), nullable=False, default=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['generation_request_id'], ['generation_requests.id'], ondelete='CASCADE'),
        sa.Index('ix_task_requirements_generation_request_id', 'generation_request_id'),
        sa.Index('ix_task_requirements_type', 'requirement_type'),
        sa.Index('ix_task_requirements_priority', 'priority')
    )
    
    # Create generation_metrics table
    op.create_table(
        'generation_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('generation_request_id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=255), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(length=50), nullable=True),
        sa.Column('metric_category', sa.String(length=100), nullable=False),
        sa.Column('metric_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['generation_request_id'], ['generation_requests.id'], ondelete='CASCADE'),
        sa.Index('ix_generation_metrics_generation_request_id', 'generation_request_id'),
        sa.Index('ix_generation_metrics_name', 'metric_name'),
        sa.Index('ix_generation_metrics_category', 'metric_category')
    )


def downgrade():
    """Remove dynamic crew generation tables."""
    
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('generation_metrics')
    op.drop_table('task_requirements')
    op.drop_table('agent_capabilities')
    op.drop_table('crew_optimizations')
    op.drop_table('generation_requests')
    op.drop_table('dynamic_crew_templates') 