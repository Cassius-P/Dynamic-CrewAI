"""Initial memory system

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create crews table
    op.create_table('crews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crews_name'), 'crews', ['name'], unique=False)
    
    # Create agents table
    op.create_table('agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=255), nullable=False),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column('backstory', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_crew_id'), 'agents', ['crew_id'], unique=False)
    op.create_index(op.f('ix_agents_name'), 'agents', ['name'], unique=False)
    
    # Create llm_providers table
    op.create_table('llm_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('provider_type', sa.String(length=50), nullable=False),
        sa.Column('api_key', sa.String(length=500), nullable=True),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_providers_name'), 'llm_providers', ['name'], unique=True)
    op.create_index(op.f('ix_llm_providers_provider_type'), 'llm_providers', ['provider_type'], unique=False)
    
    # Create executions table
    op.create_table('executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_executions_crew_id'), 'executions', ['crew_id'], unique=False)
    op.create_index(op.f('ix_executions_status'), 'executions', ['status'], unique=False)
    
    # Create memory_configurations table
    op.create_table('memory_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('short_term_retention_hours', sa.Integer(), nullable=False),
        sa.Column('short_term_max_entries', sa.Integer(), nullable=False),
        sa.Column('long_term_consolidation_threshold', sa.Float(), nullable=False),
        sa.Column('long_term_max_entries', sa.Integer(), nullable=False),
        sa.Column('entity_confidence_threshold', sa.Float(), nullable=False),
        sa.Column('entity_similarity_threshold', sa.Float(), nullable=False),
        sa.Column('embedding_provider', sa.String(length=50), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('cleanup_enabled', sa.Boolean(), nullable=False),
        sa.Column('cleanup_interval_hours', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_configurations_crew_id'), 'memory_configurations', ['crew_id'], unique=True)
    
    # Create short_term_memories table
    op.create_table('short_term_memories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('execution_id', sa.Integer(), nullable=True),
        sa.Column('relevance_score', sa.Float(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_short_term_memories_crew_id'), 'short_term_memories', ['crew_id'], unique=False)
    op.create_index(op.f('ix_short_term_memories_content_type'), 'short_term_memories', ['content_type'], unique=False)
    op.create_index(op.f('ix_short_term_memories_agent_id'), 'short_term_memories', ['agent_id'], unique=False)
    op.create_index(op.f('ix_short_term_memories_execution_id'), 'short_term_memories', ['execution_id'], unique=False)
    op.create_index(op.f('ix_short_term_memories_expires_at'), 'short_term_memories', ['expires_at'], unique=False)
    
    # Create long_term_memories table
    op.create_table('long_term_memories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('importance_score', sa.Float(), nullable=False),
        sa.Column('access_count', sa.Integer(), nullable=False),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('source_execution_id', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.ForeignKeyConstraint(['source_execution_id'], ['executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_long_term_memories_crew_id'), 'long_term_memories', ['crew_id'], unique=False)
    op.create_index(op.f('ix_long_term_memories_content_type'), 'long_term_memories', ['content_type'], unique=False)
    op.create_index(op.f('ix_long_term_memories_importance_score'), 'long_term_memories', ['importance_score'], unique=False)
    op.create_index(op.f('ix_long_term_memories_tags'), 'long_term_memories', ['tags'], unique=False)
    
    # Create entity_memories table
    op.create_table('entity_memories',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('entity_name', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('mention_count', sa.Integer(), nullable=False),
        sa.Column('first_mentioned', sa.DateTime(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entity_memories_crew_id'), 'entity_memories', ['crew_id'], unique=False)
    op.create_index(op.f('ix_entity_memories_entity_name'), 'entity_memories', ['entity_name'], unique=False)
    op.create_index(op.f('ix_entity_memories_entity_type'), 'entity_memories', ['entity_type'], unique=False)
    op.create_index(op.f('ix_entity_memories_confidence_score'), 'entity_memories', ['confidence_score'], unique=False)
    
    # Create entity_relationships table
    op.create_table('entity_relationships',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('source_entity_id', sa.String(), nullable=False),
        sa.Column('target_entity_id', sa.String(), nullable=False),
        sa.Column('relationship_type', sa.String(length=100), nullable=False),
        sa.Column('strength', sa.Float(), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.ForeignKeyConstraint(['source_entity_id'], ['entity_memories.id'], ),
        sa.ForeignKeyConstraint(['target_entity_id'], ['entity_memories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_entity_relationships_crew_id'), 'entity_relationships', ['crew_id'], unique=False)
    op.create_index(op.f('ix_entity_relationships_source_entity_id'), 'entity_relationships', ['source_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_relationships_target_entity_id'), 'entity_relationships', ['target_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_relationships_relationship_type'), 'entity_relationships', ['relationship_type'], unique=False)
    
    # Create memory_cleanup_logs table
    op.create_table('memory_cleanup_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('crew_id', sa.Integer(), nullable=False),
        sa.Column('cleanup_type', sa.String(length=50), nullable=False),
        sa.Column('entries_removed', sa.Integer(), nullable=False),
        sa.Column('cleanup_reason', sa.String(length=255), nullable=True),
        sa.Column('execution_time_seconds', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['crew_id'], ['crews.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_memory_cleanup_logs_crew_id'), 'memory_cleanup_logs', ['crew_id'], unique=False)
    op.create_index(op.f('ix_memory_cleanup_logs_cleanup_type'), 'memory_cleanup_logs', ['cleanup_type'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('memory_cleanup_logs')
    op.drop_table('entity_relationships')
    op.drop_table('entity_memories')
    op.drop_table('long_term_memories')
    op.drop_table('short_term_memories')
    op.drop_table('memory_configurations')
    op.drop_table('executions')
    op.drop_table('llm_providers')
    op.drop_table('agents')
    op.drop_table('crews')
    
    # Drop pgvector extension
    op.execute('DROP EXTENSION IF EXISTS vector') 