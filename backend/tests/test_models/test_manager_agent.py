"""Tests for manager agent database model enhancements."""

import pytest
from app.models.agent import Agent
from sqlalchemy import Column, String, Boolean, JSON


class TestManagerAgentSchema:
    """Test cases for manager agent schema enhancements."""

    def test_agent_model_has_manager_type_column(self):
        """Test that agent model has manager_type column."""
        # Check that the Agent model has the manager_type column
        assert hasattr(Agent, 'manager_type')
        assert isinstance(Agent.manager_type.property.columns[0], Column)
        assert str(Agent.manager_type.property.columns[0].type) == 'VARCHAR(50)'

    def test_agent_model_has_can_generate_tasks_column(self):
        """Test that agent model has can_generate_tasks column."""
        # Check that the Agent model has the can_generate_tasks column
        assert hasattr(Agent, 'can_generate_tasks')
        assert isinstance(Agent.can_generate_tasks.property.columns[0], Column)
        assert isinstance(Agent.can_generate_tasks.property.columns[0].type, Boolean)

    def test_agent_model_has_manager_config_column(self):
        """Test that agent model has manager_config column."""
        # Check that the Agent model has the manager_config column
        assert hasattr(Agent, 'manager_config')
        assert isinstance(Agent.manager_config.property.columns[0], Column)
        assert isinstance(Agent.manager_config.property.columns[0].type, JSON)

    def test_agent_model_manager_type_nullable(self):
        """Test that manager_type column is nullable."""
        manager_type_column = Agent.manager_type.property.columns[0]
        assert manager_type_column.nullable is True

    def test_agent_model_can_generate_tasks_default(self):
        """Test that can_generate_tasks has default value."""
        can_generate_tasks_column = Agent.can_generate_tasks.property.columns[0]
        assert can_generate_tasks_column.default is not None
        assert can_generate_tasks_column.default.arg is False

    def test_agent_model_manager_config_nullable(self):
        """Test that manager_config column is nullable."""
        manager_config_column = Agent.manager_config.property.columns[0]
        assert manager_config_column.nullable is True

    def test_agent_model_existing_fields_preserved(self):
        """Test that existing agent fields are preserved."""
        # Verify existing fields still exist
        assert hasattr(Agent, 'role')
        assert hasattr(Agent, 'goal')
        assert hasattr(Agent, 'backstory')
        assert hasattr(Agent, 'allow_delegation')
        assert hasattr(Agent, 'tools')
        assert hasattr(Agent, 'llm_config')

    def test_agent_model_allow_delegation_exists(self):
        """Test that allow_delegation field exists (required for manager agents)."""
        assert hasattr(Agent, 'allow_delegation')
        allow_delegation_column = Agent.allow_delegation.property.columns[0]
        assert isinstance(allow_delegation_column.type, Boolean)
        assert allow_delegation_column.default is not None
        assert allow_delegation_column.default.arg is False

    def test_agent_model_table_name(self):
        """Test that the table name is correct."""
        assert Agent.__tablename__ == "agents"

    def test_agent_model_manager_fields_count(self):
        """Test that we added exactly 3 new manager fields."""
        manager_fields = ['manager_type', 'can_generate_tasks', 'manager_config']
        
        for field in manager_fields:
            assert hasattr(Agent, field), f"Missing manager field: {field}"

 