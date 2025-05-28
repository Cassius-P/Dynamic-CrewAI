"""Tests for generation service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.generation_service import GenerationService
from app.models.generation import GenerationRequest, DynamicCrewTemplate
from app.models.crew import Crew
from app.schemas.generation import (
    GenerationRequestCreate, GenerationResult, TaskAnalysisRequest,
    CrewValidationRequest, CrewOptimizationRequest, DynamicCrewTemplateCreate,
    GenerationRequestResponse, TaskAnalysisResponse, CrewValidationResponse,
    CrewOptimizationResponse, DynamicCrewTemplateResponse, BulkGenerationResponse
)


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def service(mock_db):
    """Create service instance with mocked database."""
    return GenerationService(mock_db)


@pytest.mark.asyncio
class TestGenerationService:
    """Test cases for GenerationService."""
    
    async def test_create_generation_request_success(self, service, mock_db):
        """Test successful generation request creation."""
        request = GenerationRequestCreate(
            objective="Create a comprehensive marketing strategy for a new product launch",
            requirements={"budget": "moderate", "timeline": "3 weeks"},
            llm_provider="openai",
            optimization_enabled=False  # Disable optimization to avoid Mock issues
        )
        
        # Mock database objects
        mock_generation_request = Mock(spec=GenerationRequest)
        mock_generation_request.id = 1
        mock_generation_request.objective = request.objective
        mock_generation_request.generation_status = "completed"
        mock_generation_request.created_at = datetime.utcnow()
        mock_generation_request.completed_at = datetime.utcnow()
        mock_generation_request.requirements = request.requirements
        mock_generation_request.generated_crew_id = 123
        mock_generation_request.template_id = None
        mock_generation_request.llm_provider = "openai"
        mock_generation_request.optimization_applied = False
        mock_generation_request.generation_time_seconds = 5.5
        mock_generation_request.generation_result = None
        mock_generation_request.validation_result = None
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db.execute.return_value = None
        
        # Mock the generator
        mock_generation_result = GenerationResult(
            crew_config={"name": "Test Crew", "process": "hierarchical"},
            agent_configs=[{"role": "Strategist"}],
            task_configs=[{"description": "Strategy task"}],
            manager_config={"role": "Manager"},
            tool_assignments={"Strategist": ["research_tool"]},
            estimated_performance={"success_rate": 0.8}
        )
        
        with patch.object(service.generator, 'generate_crew', return_value=mock_generation_result):
            with patch.object(service, '_create_crew_from_config', return_value=123):
                with patch.object(service, '_record_generation_metrics'):
                    with patch.object(service, '_to_generation_response') as mock_to_response:
                        mock_to_response.return_value = GenerationRequestResponse(
                            id=1,
                            objective=request.objective,
                            requirements=request.requirements,
                            generated_crew_id=123,
                            template_id=None,
                            llm_provider="openai",
                            generation_status="completed",
                            generation_result=mock_generation_result,
                            validation_result=None,
                            optimization_applied=False,
                            generation_time_seconds=5.5,
                            created_at=datetime.utcnow(),
                            completed_at=datetime.utcnow()
                        )
                        
                        result = await service.create_generation_request(request)
                        
                        assert mock_db.add.called
                        assert mock_db.commit.called
                        assert service.generator.generate_crew.called
    
    async def test_create_generation_request_with_template(self, service, mock_db):
        """Test generation request with template."""
        request = GenerationRequestCreate(
            objective="Analyze customer feedback data",
            template_id=1,
            llm_provider="openai",
            optimization_enabled=False  # Disable optimization to avoid crew lookup issues
        )
        
        # Mock template
        mock_template = Mock(spec=DynamicCrewTemplate)
        mock_template.id = 1
        mock_template.is_active = True
        
        # Set up query chain - first call returns template, second would be for crew (but won't be called)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        # Mock other database operations
        mock_generation_request = Mock(spec=GenerationRequest)
        mock_generation_request.id = 1
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db.execute.return_value = None
        
        mock_generation_result = GenerationResult(
            crew_config={"name": "Analysis Crew"},
            agent_configs=[{"role": "Analyst"}],
            task_configs=[{"description": "Analysis task"}],
            manager_config={"role": "Manager"},
            tool_assignments={"Analyst": ["analysis_tool"]},
            estimated_performance={"success_rate": 0.85}
        )
        
        with patch.object(service.generator, 'generate_crew', return_value=mock_generation_result):
            with patch.object(service, '_create_crew_from_config', return_value=456):
                with patch.object(service, '_record_generation_metrics'):
                    with patch.object(service, '_update_template_usage'):
                        with patch.object(service, '_to_generation_response') as mock_to_response:
                            mock_to_response.return_value = GenerationRequestResponse(
                                id=1,
                                objective=request.objective,
                                requirements=None,
                                generated_crew_id=456,
                                template_id=1,
                                llm_provider="openai",
                                generation_status="completed",
                                generation_result=mock_generation_result,
                                validation_result=None,
                                optimization_applied=False,
                                generation_time_seconds=5.5,
                                created_at=datetime.utcnow(),
                                completed_at=datetime.utcnow()
                            )
                            
                            result = await service.create_generation_request(request)
                            
                            service._update_template_usage.assert_called_with(1, True)
    
    async def test_create_generation_request_template_not_found(self, service, mock_db):
        """Test generation request with non-existent template."""
        request = GenerationRequestCreate(
            objective="Test objective with invalid template",
            template_id=999
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="Template 999 not found or inactive"):
            await service.create_generation_request(request)
    
    async def test_create_generation_request_generation_failure(self, service, mock_db):
        """Test generation request when crew generation fails."""
        request = GenerationRequestCreate(
            objective="Test objective that will fail"
        )
        
        mock_generation_request = Mock(spec=GenerationRequest)
        mock_generation_request.id = 1
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        mock_db.execute.return_value = None
        
        with patch.object(service.generator, 'generate_crew', side_effect=Exception("Generation failed")):
            with pytest.raises(Exception, match="Generation failed"):
                await service.create_generation_request(request)
            
            # Verify status was updated to failed
            mock_db.execute.assert_called()
    
    async def test_get_generation_request_found(self, service, mock_db):
        """Test retrieving existing generation request."""
        request_id = 1
        
        mock_request = Mock(spec=GenerationRequest)
        mock_request.id = request_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_request
        
        with patch.object(service, '_to_generation_response') as mock_to_response:
            mock_to_response.return_value = GenerationRequestResponse(
                id=1,
                objective="Test objective",
                requirements=None,
                generated_crew_id=None,
                template_id=None,
                llm_provider="openai",
                generation_status="completed",
                generation_result=None,
                validation_result=None,
                optimization_applied=False,
                generation_time_seconds=None,
                created_at=datetime.utcnow(),
                completed_at=None
            )
            
            result = await service.get_generation_request(request_id)
            
            assert result is not None
            mock_to_response.assert_called_with(mock_request)
    
    async def test_get_generation_request_not_found(self, service, mock_db):
        """Test retrieving non-existent generation request."""
        request_id = 999
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await service.get_generation_request(request_id)
        
        assert result is None
    
    async def test_list_generation_requests(self, service, mock_db):
        """Test listing generation requests with pagination."""
        mock_requests = [Mock(spec=GenerationRequest) for _ in range(3)]
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_requests
        
        with patch.object(service, '_to_generation_response') as mock_to_response:
            mock_to_response.side_effect = [
                GenerationRequestResponse(
                    id=i + 1,
                    objective=f"Objective {i + 1}",
                    requirements=None,
                    generated_crew_id=None,
                    template_id=None,
                    llm_provider="openai",
                    generation_status="completed",
                    generation_result=None,
                    validation_result=None,
                    optimization_applied=False,
                    generation_time_seconds=None,
                    created_at=datetime.utcnow(),
                    completed_at=None
                ) for i in range(3)
            ]
            
            result = await service.list_generation_requests(skip=0, limit=10)
            
            assert len(result) == 3
            assert mock_to_response.call_count == 3
    
    async def test_analyze_task(self, service):
        """Test task analysis functionality."""
        request = TaskAnalysisRequest(
            objective="Build a web application for e-commerce",
            context="Small business needs online presence",
            domain="web_development"
        )
        
        with patch.object(service.generator, '_analyze_task_requirements') as mock_analyze:
            mock_analyze.return_value = TaskAnalysisResponse(
                objective=request.objective,
                complexity_score=7.5,
                estimated_duration_hours=40,
                required_skills=["programming", "design"],
                required_tools=["development_tools"],
                task_requirements=[],
                domain_category="web_development",
                risk_factors=[]
            )
            
            result = await service.analyze_task(request)
            
            mock_analyze.assert_called_once()
            # Check the call was made with the correct parameters
            call_args = mock_analyze.call_args
            assert call_args is not None
            if call_args.args:
                assert call_args.args[0] == request.objective
            elif 'objective' in call_args.kwargs:
                assert call_args.kwargs['objective'] == request.objective
    
    async def test_validate_crew_configuration(self, service):
        """Test crew configuration validation."""
        request = CrewValidationRequest(
            crew_config={"name": "Test Crew", "agents": [{"role": "Tester"}]},
            objective="Test software quality"
        )
        
        with patch.object(service.generator, 'validate_crew_configuration') as mock_validate:
            mock_validate.return_value = CrewValidationResponse(
                valid=True,
                validation_score=8.5,
                issues=[],
                warnings=[],
                recommendations=[],
                capability_coverage={},
                estimated_success_rate=0.85
            )
            
            result = await service.validate_crew_configuration(request)
            
            mock_validate.assert_called_once_with(
                crew_config=request.crew_config,
                objective=request.objective
            )
    
    async def test_optimize_crew_success(self, service, mock_db):
        """Test successful crew optimization."""
        request = CrewOptimizationRequest(
            crew_id=1,
            optimization_type="performance",
            target_metrics={"efficiency": 0.8}
        )
        
        # Mock crew with real config data
        mock_crew = Mock(spec=Crew)
        mock_crew.id = 1
        mock_crew.config = {"max_rpm": 10, "memory": False}  # Real dict instead of Mock
        mock_db.query.return_value.filter.return_value.first.return_value = mock_crew
        
        # Mock optimization record
        mock_optimization = Mock()
        mock_optimization.id = 1
        mock_optimization.crew_id = 1
        mock_optimization.optimization_type = "performance"
        mock_optimization.optimization_score = 7.5
        mock_optimization.optimization_metrics = {}
        mock_optimization.applied = False
        mock_optimization.created_at = datetime.utcnow()
        mock_optimization.applied_at = None
        mock_optimization.original_config = {"crew": {"max_rpm": 10, "memory": False}}
        
        # Mock database operations
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Make refresh update the mock optimization attributes
        def mock_refresh(obj):
            if hasattr(obj, 'optimization_score'):
                obj.optimization_score = 7.5
                obj.optimization_metrics = {"type": "performance", "improvements": {}}
        
        mock_db.refresh.side_effect = mock_refresh
        mock_db.execute.return_value = None
        
        with patch.object(service, '_apply_optimization_logic', return_value={"max_rpm": 15}):
            with patch.object(service, '_calculate_optimization_score', return_value=7.5):
                with patch.object(service, '_calculate_improvements', return_value={}):
                    with patch.object(service, '_to_optimization_response') as mock_to_response:
                        mock_to_response.return_value = CrewOptimizationResponse(
                            id=1,
                            crew_id=1,
                            optimization_type="performance",
                            optimization_score=7.5,
                            optimization_metrics={"type": "performance", "improvements": {}},
                            applied=False,
                            created_at=datetime.utcnow(),
                            applied_at=None
                        )
                        
                        result = await service.optimize_crew(request)
                        
                        assert mock_db.add.called
                        assert mock_db.commit.called
    
    async def test_optimize_crew_not_found(self, service, mock_db):
        """Test crew optimization with non-existent crew."""
        request = CrewOptimizationRequest(
            crew_id=999,
            optimization_type="performance"
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(ValueError, match="Crew 999 not found"):
            await service.optimize_crew(request)
    
    async def test_bulk_generate(self, service):
        """Test bulk crew generation."""
        from app.schemas.generation import BulkGenerationRequest
        
        request = BulkGenerationRequest(
            objectives=[
                "Create marketing campaign",
                "Analyze customer data",
                "Develop mobile app"
            ],
            shared_requirements={"budget": "moderate"},
            llm_provider="openai"
        )
        
        # Mock individual generation requests
        mock_results = []
        for i in range(3):
            mock_result = GenerationRequestResponse(
                id=i + 1,
                objective=request.objectives[i],
                requirements=request.shared_requirements,
                generated_crew_id=None,
                template_id=None,
                llm_provider="openai",
                generation_status="completed" if i < 2 else "failed",
                generation_result=None,
                validation_result=None,
                optimization_applied=False,
                generation_time_seconds=5.0,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            mock_results.append(mock_result)
        
        # Mock create_generation_request to avoid actual crew optimization
        async def mock_create_request(req):
            # Return result based on objective index
            obj_index = request.objectives.index(req.objective)
            return mock_results[obj_index]
        
        with patch.object(service, 'create_generation_request', side_effect=mock_create_request):
            result = await service.bulk_generate(request)
            
            assert result.total_requests == 3
            assert result.successful_generations == 2
            assert result.failed_generations == 1
            assert len(result.generation_requests) == 3
    
    async def test_create_template(self, service, mock_db):
        """Test creating a new template."""
        template_data = DynamicCrewTemplateCreate(
            name="Analytics Team Template",
            description="Template for data analysis teams",
            template_type="analytics",
            template_config={"preferred_tools": ["analysis_tool"]}
        )
        
        mock_template = Mock(spec=DynamicCrewTemplate)
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        with patch.object(service, '_to_template_response') as mock_to_response:
            mock_to_response.return_value = DynamicCrewTemplateResponse(
                id=1,
                name=template_data.name,
                description=template_data.description,
                template_type=template_data.template_type,
                template_config=template_data.template_config,
                success_rate=0.0,
                usage_count=0,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=None
            )
            
            result = await service.create_template(template_data)
            
            assert mock_db.add.called
            assert mock_db.commit.called
            mock_to_response.assert_called_once()
    
    async def test_get_template_found(self, service, mock_db):
        """Test retrieving existing template."""
        template_id = 1
        
        mock_template = Mock(spec=DynamicCrewTemplate)
        mock_template.id = template_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        with patch.object(service, '_to_template_response') as mock_to_response:
            mock_to_response.return_value = DynamicCrewTemplateResponse(
                id=1,
                name="Test Template",
                description=None,
                template_type="test",
                template_config={},
                success_rate=0.0,
                usage_count=0,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=None
            )
            
            result = await service.get_template(template_id)
            
            assert result is not None
            mock_to_response.assert_called_with(mock_template)
    
    async def test_get_template_not_found(self, service, mock_db):
        """Test retrieving non-existent template."""
        template_id = 999
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await service.get_template(template_id)
        
        assert result is None
    
    async def test_list_templates(self, service, mock_db):
        """Test listing templates with pagination."""
        mock_templates = [Mock(spec=DynamicCrewTemplate) for _ in range(2)]
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_templates
        
        with patch.object(service, '_to_template_response') as mock_to_response:
            mock_to_response.side_effect = [
                DynamicCrewTemplateResponse(
                    id=i + 1,
                    name=f"Template {i + 1}",
                    description=None,
                    template_type="test",
                    template_config={},
                    success_rate=0.0,
                    usage_count=0,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=None
                ) for i in range(2)
            ]
            
            result = await service.list_templates(skip=0, limit=10)
            
            assert len(result) == 2
            assert mock_to_response.call_count == 2
    
    async def test_update_template_success(self, service, mock_db):
        """Test successful template update."""
        from app.schemas.generation import DynamicCrewTemplateUpdate
        
        template_id = 1
        update_data = DynamicCrewTemplateUpdate(
            name="Updated Template Name",
            is_active=False
        )
        
        mock_template = Mock(spec=DynamicCrewTemplate)
        mock_template.id = template_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        with patch.object(service, '_to_template_response') as mock_to_response:
            mock_to_response.return_value = DynamicCrewTemplateResponse(
                id=1,
                name="Updated Template Name",
                description=None,
                template_type="test",
                template_config={},
                success_rate=0.0,
                usage_count=0,
                is_active=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            result = await service.update_template(template_id, update_data)
            
            assert result is not None
            assert mock_db.execute.called
            assert mock_db.commit.called
    
    async def test_update_template_not_found(self, service, mock_db):
        """Test updating non-existent template."""
        from app.schemas.generation import DynamicCrewTemplateUpdate
        
        template_id = 999
        update_data = DynamicCrewTemplateUpdate(name="New Name")
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await service.update_template(template_id, update_data)
        
        assert result is None
    
    async def test_create_crew_from_config(self, service, mock_db):
        """Test creating crew from generation result."""
        generation_result = GenerationResult(
            crew_config={"name": "Test Crew", "description": "Test crew"},
            agent_configs=[
                {"name": "Agent1", "role": "Analyst", "goal": "Analyze data"},
                {"name": "Agent2", "role": "Writer", "goal": "Write reports"}
            ],
            task_configs=[],
            manager_config={},
            tool_assignments={},
            estimated_performance={}
        )
        
        # Mock the database operations but don't try to pass invalid parameters
        mock_crew = Mock(spec=Crew)
        mock_crew.id = 123
        
        # Mock the add/commit/refresh cycle
        def mock_add(obj):
            if hasattr(obj, 'id'):
                obj.id = 123  # Set ID for the crew
        
        mock_db.add.side_effect = mock_add
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        result = await service._create_crew_from_config(generation_result, 1)
        
        assert result == 123
        assert mock_db.add.call_count >= 3  # Crew + 2 agents
        assert mock_db.commit.call_count >= 1
    
    async def test_record_generation_metrics(self, service, mock_db):
        """Test recording generation metrics."""
        generation_result = GenerationResult(
            crew_config={},
            agent_configs=[{}, {}],  # 2 agents
            task_configs=[],
            manager_config={},
            tool_assignments={},
            estimated_performance={"estimated_success_rate": 0.8}
        )
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        await service._record_generation_metrics(1, generation_result, 5.5)
        
        # Should add 3 metrics: generation_time, agent_count, estimated_success_rate
        assert mock_db.add.call_count == 3
        assert mock_db.commit.called
    
    async def test_update_template_usage(self, service, mock_db):
        """Test updating template usage statistics."""
        template_id = 1
        
        mock_template = Mock(spec=DynamicCrewTemplate)
        mock_template.id = template_id
        mock_template.usage_count = 5
        mock_template.success_rate = 0.8
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        mock_db.execute.return_value = None
        mock_db.commit.return_value = None
        
        await service._update_template_usage(template_id, True)
        
        assert mock_db.execute.called
        assert mock_db.commit.called 