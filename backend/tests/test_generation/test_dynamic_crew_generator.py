"""Tests for dynamic crew generator."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.core.dynamic_crew_generator import DynamicCrewGenerator
from app.core.llm_wrapper import LLMWrapper
from app.core.tool_registry import ToolRegistry
from app.models.generation import DynamicCrewTemplate
from app.schemas.generation import GenerationResult, TaskAnalysisResponse, CrewCompositionSuggestion


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_llm_wrapper():
    """Mock LLM wrapper."""
    return Mock(spec=LLMWrapper)


@pytest.fixture
def mock_tool_registry():
    """Mock tool registry."""
    registry = Mock(spec=ToolRegistry)
    registry.get_available_tools.return_value = [
        {"name": "research_tool", "description": "Research information"},
        {"name": "analysis_tool", "description": "Analyze data"},
        {"name": "writing_tool", "description": "Write content"}
    ]
    return registry


@pytest.fixture
def generator(mock_db, mock_llm_wrapper, mock_tool_registry):
    """Create generator instance with mocks."""
    return DynamicCrewGenerator(mock_db, mock_llm_wrapper, mock_tool_registry)


@pytest.mark.asyncio
class TestDynamicCrewGenerator:
    """Test cases for DynamicCrewGenerator."""
    
    async def test_generate_crew_basic(self, generator, mock_db):
        """Test basic crew generation."""
        objective = "Create a marketing campaign for a new product"
        
        # Mock LLM responses
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.side_effect = [
                # Task analysis response
                json.dumps({
                    "complexity_score": 6.0,
                    "estimated_duration_hours": 12.0,
                    "required_skills": ["marketing", "creativity", "analysis"],
                    "required_tools": ["research_tool", "writing_tool"],
                    "domain_category": "marketing",
                    "risk_factors": ["tight_deadline"]
                }),
                # Crew composition response
                json.dumps({
                    "agents": [
                        {
                            "role": "Marketing Strategist",
                            "description": "Develops marketing strategies",
                            "required_skills": ["marketing", "strategy"],
                            "suggested_tools": ["research_tool"],
                            "priority": 5
                        },
                        {
                            "role": "Content Creator",
                            "description": "Creates marketing content",
                            "required_skills": ["creativity", "writing"],
                            "suggested_tools": ["writing_tool"],
                            "priority": 4
                        }
                    ]
                }),
                # Agent config responses
                json.dumps({
                    "goal": "Develop comprehensive marketing strategy",
                    "backstory": "Expert marketing strategist with 10 years experience",
                    "allow_delegation": True,
                    "max_iter": 12
                }),
                json.dumps({
                    "goal": "Create engaging marketing content",
                    "backstory": "Creative content creator with expertise in multiple formats",
                    "allow_delegation": False,
                    "max_iter": 8
                }),
                # Tool selection responses
                json.dumps({"selected_tools": ["research_tool"]}),
                json.dumps({"selected_tools": ["writing_tool"]})
            ]
            
            result = await generator.generate_crew(objective)
            
            assert isinstance(result, GenerationResult)
            assert result.crew_config["name"].startswith("Dynamic Crew for:")
            assert result.crew_config["process"] == "hierarchical"
            assert len(result.agent_configs) == 2
            assert result.manager_config["role"] == "Manager"
            assert "research_tool" in result.tool_assignments.get("Marketing Strategist", [])
            assert "writing_tool" in result.tool_assignments.get("Content Creator", [])
    
    async def test_generate_crew_with_template(self, generator, mock_db):
        """Test crew generation with template."""
        objective = "Analyze customer data"
        template_id = 1
        
        # Mock template
        mock_template = Mock(spec=DynamicCrewTemplate)
        mock_template.template_config = {
            "preferred_agents": ["Data Analyst", "Researcher"],
            "optimization": "accuracy"
        }
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.side_effect = [
                json.dumps({
                    "complexity_score": 4.0,
                    "estimated_duration_hours": 6.0,
                    "required_skills": ["data_analysis"],
                    "required_tools": ["analysis_tool"],
                    "domain_category": "analytics",
                    "risk_factors": []
                }),
                json.dumps({
                    "agents": [
                        {
                            "role": "Data Analyst",
                            "description": "Analyzes customer data",
                            "required_skills": ["data_analysis"],
                            "suggested_tools": ["analysis_tool"],
                            "priority": 5
                        }
                    ]
                }),
                json.dumps({
                    "goal": "Analyze customer data patterns",
                    "backstory": "Experienced data analyst",
                    "allow_delegation": False,
                    "max_iter": 10
                }),
                json.dumps({"selected_tools": ["analysis_tool"]})
            ]
            
            result = await generator.generate_crew(objective, template_id=template_id)
            
            assert isinstance(result, GenerationResult)
            assert len(result.agent_configs) == 1
            assert result.agent_configs[0]["role"] == "Data Analyst"
    
    async def test_generate_crew_invalid_objective(self, generator):
        """Test crew generation with invalid objective."""
        with pytest.raises(ValueError, match="Objective must be at least 10 characters"):
            await generator.generate_crew("short")
    
    async def test_generate_crew_template_not_found(self, generator, mock_db):
        """Test crew generation with non-existent template."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="Template 999 not found or inactive"):
            await generator.generate_crew("Valid objective here", template_id=999)
    
    async def test_analyze_task_requirements(self, generator):
        """Test task analysis functionality."""
        objective = "Build a web application"
        requirements = {"deadline": "2 weeks", "budget": "limited"}
        
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                "complexity_score": 7.5,
                "estimated_duration_hours": 80.0,
                "required_skills": ["programming", "design", "testing"],
                "required_tools": ["development_tools", "testing_tools"],
                "domain_category": "software_development",
                "risk_factors": ["tight_deadline", "limited_budget"]
            })
            
            result = await generator._analyze_task_requirements(objective, requirements)
            
            assert isinstance(result, TaskAnalysisResponse)
            assert result.objective == objective
            assert result.complexity_score == 7.5
            assert result.estimated_duration_hours == 80.0
            assert "programming" in result.required_skills
            assert "software_development" == result.domain_category
    
    async def test_analyze_task_requirements_fallback(self, generator):
        """Test task analysis with fallback when LLM fails."""
        objective = "Test objective"
        
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.return_value = "invalid json response"
            
            result = await generator._analyze_task_requirements(objective)
            
            assert isinstance(result, TaskAnalysisResponse)
            assert result.objective == objective
            assert result.complexity_score == 5.0
            assert result.domain_category == "general"
    
    async def test_generate_crew_composition(self, generator):
        """Test crew composition generation."""
        task_analysis = TaskAnalysisResponse(
            objective="Test project",
            complexity_score=5.0,
            estimated_duration_hours=10.0,
            required_skills=["skill1", "skill2"],
            required_tools=["tool1"],
            task_requirements=[],
            domain_category="test",
            risk_factors=[]
        )
        
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                "agents": [
                    {
                        "role": "Specialist",
                        "description": "Subject matter expert",
                        "required_skills": ["skill1"],
                        "suggested_tools": ["tool1"],
                        "priority": 4
                    }
                ]
            })
            
            result = await generator._generate_crew_composition(task_analysis)
            
            assert len(result) == 1
            assert isinstance(result[0], CrewCompositionSuggestion)
            assert result[0].agent_role == "Specialist"
            assert result[0].priority == 4
    
    async def test_generate_agent_configurations(self, generator):
        """Test agent configuration generation."""
        suggestions = [
            CrewCompositionSuggestion(
                agent_role="Developer",
                agent_description="Develops software",
                required_skills=["programming"],
                suggested_tools=["dev_tools"],
                priority=5
            )
        ]
        
        task_analysis = TaskAnalysisResponse(
            objective="Build software",
            complexity_score=6.0,
            estimated_duration_hours=20.0,
            required_skills=["programming"],
            required_tools=["dev_tools"],
            task_requirements=[],
            domain_category="software",
            risk_factors=[]
        )
        
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                "goal": "Develop high-quality software",
                "backstory": "Experienced software developer",
                "allow_delegation": True,
                "max_iter": 15
            })
            
            result = await generator._generate_agent_configurations(suggestions, task_analysis)
            
            assert len(result) == 1
            assert result[0]["role"] == "Developer"
            assert result[0]["goal"] == "Develop high-quality software"
            assert result[0]["allow_delegation"] is True
    
    async def test_select_and_assign_tools(self, generator):
        """Test tool selection and assignment."""
        agent_configs = [
            {
                "role": "Analyst",
                "skills": ["analysis"],
                "suggested_tools": ["analysis_tool"]
            }
        ]
        
        task_analysis = TaskAnalysisResponse(
            objective="Analyze data",
            complexity_score=4.0,
            estimated_duration_hours=8.0,
            required_skills=["analysis"],
            required_tools=["analysis_tool"],
            task_requirements=[],
            domain_category="analytics",
            risk_factors=[]
        )
        
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                "selected_tools": ["analysis_tool"]
            })
            
            result = await generator._select_and_assign_tools(agent_configs, task_analysis)
            
            assert "Analyst" in result
            assert "analysis_tool" in result["Analyst"]
    
    async def test_generate_manager_configuration(self, generator):
        """Test manager configuration generation."""
        agent_configs = [
            {"role": "Worker1", "skills": ["skill1"]},
            {"role": "Worker2", "skills": ["skill2"]}
        ]
        
        task_analysis = TaskAnalysisResponse(
            objective="Coordinate team work",
            complexity_score=5.0,
            estimated_duration_hours=15.0,
            required_skills=["management"],
            required_tools=["management_tools"],
            task_requirements=[],
            domain_category="management",
            risk_factors=[]
        )
        
        tool_assignments = {
            "Worker1": ["tool1"],
            "Worker2": ["tool2"]
        }
        
        result = await generator._generate_manager_configuration(
            agent_configs, task_analysis, tool_assignments
        )
        
        assert result["role"] == "Manager"
        assert result["allow_delegation"] is True
        assert "Worker1" in result["managed_agents"]
        assert "Worker2" in result["managed_agents"]
        assert result["coordination_style"] == "hierarchical"
    
    async def test_validate_crew_configuration(self, generator):
        """Test crew configuration validation."""
        crew_config = {
            "name": "Test Crew",
            "agents": [{"role": "Tester"}],
            "process": "hierarchical"
        }
        objective = "Test the system"
        
        with patch.object(generator, 'generate_response_with_llm') as mock_llm:
            mock_llm.return_value = json.dumps({
                "valid": True,
                "validation_score": 8.5,
                "issues": [],
                "warnings": ["Consider adding more agents"],
                "recommendations": ["Add specialist roles"],
                "capability_coverage": {"testing": 0.8},
                "estimated_success_rate": 0.85
            })
            
            result = await generator.validate_crew_configuration(crew_config, objective)
            
            assert result.valid is True
            assert result.validation_score == 8.5
            assert len(result.warnings) == 1
            assert result.estimated_success_rate == 0.85
    
    async def test_llm_generation_fallback(self, generator):
        """Test fallback behavior when LLM generation fails."""
        with patch.object(generator.llm_wrapper, 'create_llm_from_config') as mock_create:
            mock_create.side_effect = Exception("LLM failed")
            
            result = await generator.generate_response_with_llm("test prompt")
            
            # Should return fallback response
            assert isinstance(result, str)
            assert result != ""
    
    async def test_estimate_crew_performance(self, generator):
        """Test crew performance estimation."""
        crew_config = {"name": "Test Crew", "process": "hierarchical"}
        agent_configs = [
            {"role": "Agent1", "suggested_tools": ["tool1"]},
            {"role": "Agent2", "suggested_tools": ["tool2"]}
        ]
        task_configs = [{"description": "Main task"}]
        
        task_analysis = TaskAnalysisResponse(
            objective="Complete project",
            complexity_score=6.0,
            estimated_duration_hours=24.0,
            required_skills=["skill1", "skill2"],
            required_tools=["tool1", "tool2"],
            task_requirements=[],
            domain_category="general",
            risk_factors=[]
        )
        
        result = await generator._estimate_crew_performance(
            crew_config, agent_configs, task_configs, task_analysis
        )
        
        assert "estimated_success_rate" in result
        assert "efficiency_score" in result
        assert "cost_score" in result
        assert "overall_score" in result
        assert 0.0 <= result["estimated_success_rate"] <= 1.0
        assert 0.0 <= result["overall_score"] <= 1.0 